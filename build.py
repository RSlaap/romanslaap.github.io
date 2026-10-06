#!/usr/bin/env python3
"""Build the website and every resume variant from data/career.yaml.

    python build.py            # site + all resume PDFs
    python build.py --no-pdf   # site only (fast, no browser needed)

Output:
    _site/          the deployable website (published resumes in _site/resume/)
    dist/resumes/   every resume variant as HTML + PDF
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).parent
SITE_DIR = ROOT / "_site"
RESUME_DIR = ROOT / "dist" / "resumes"


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def fail(message):
    sys.exit(f"build error: {message}")


def validate_career(career):
    known_tags = set(career["tags"])
    skill_ids = [skill["id"] for skill in career["skills"]]
    duplicates = {skill_id for skill_id in skill_ids if skill_ids.count(skill_id) > 1}
    if duplicates:
        fail(f"duplicate skill id(s) {sorted(duplicates)}")
    for skill in career["skills"]:
        if skill["group"] not in career["skill_groups"]:
            fail(f"unknown group '{skill['group']}' for skill '{skill['id']}'")
    unused_skills = set(skill_ids)
    seen_ids = set()
    for entry in career["experience"]:
        for position in entry["positions"]:
            if position["id"] in seen_ids:
                fail(f"duplicate position id '{position['id']}'")
            if "client_of" in position and position["client_of"] not in seen_ids:
                fail(f"client_of '{position['client_of']}' in position '{position['id']}' must be a position listed above it")
            seen_ids.add(position["id"])
            for bullet in position["bullets"]:
                unknown = set(bullet.get("tags", [])) - known_tags
                if unknown:
                    fail(f"unknown tag(s) {sorted(unknown)} in position '{position['id']}'")
            unknown = set(position.get("used", [])) - set(skill_ids)
            if unknown:
                fail(f"unknown skill(s) {sorted(unknown)} in position '{position['id']}'")
            unused_skills -= set(position.get("used", []))
    if unused_skills:
        fail(f"skill(s) {sorted(unused_skills)} not used by any position; add them to a position's `used:` or remove them")
    for page in career["about_pages"]:
        if "summary" in page:
            page["content"] = career["summaries"][page["summary"]]
    return seen_ids


def validate_variant(name, variant, career, position_ids):
    unknown_tags = set(variant["tags"]) - set(career["tags"])
    if unknown_tags:
        fail(f"resumes/{name}.yaml: unknown tag(s) {sorted(unknown_tags)}")
    unknown_positions = set(variant.get("exclude_positions", [])) - position_ids
    if unknown_positions:
        fail(f"resumes/{name}.yaml: unknown position id(s) {sorted(unknown_positions)}")
    unknown_groups = set(variant["skill_groups"]) - set(career["skill_groups"])
    if unknown_groups:
        fail(f"resumes/{name}.yaml: unknown skill group(s) {sorted(unknown_groups)}")
    unknown_skills = set(variant.get("exclude_skills", [])) - {skill["id"] for skill in career["skills"]}
    if unknown_skills:
        fail(f"resumes/{name}.yaml: unknown skill(s) in exclude_skills {sorted(unknown_skills)}")
    if variant["summary"] not in career["summaries"]:
        fail(f"resumes/{name}.yaml: unknown summary '{variant['summary']}'")
    unknown_certs = set(variant.get("certifications", [])) - {cert["name"] for cert in career["certifications"]}
    if unknown_certs:
        fail(f"resumes/{name}.yaml: unknown certification(s) {sorted(unknown_certs)}")
    unknown_notes = set(variant.get("position_notes", {})) - position_ids
    if unknown_notes:
        fail(f"resumes/{name}.yaml: position_notes for unknown position id(s) {sorted(unknown_notes)}")


def select_bullets(bullets, tags, limit):
    """Keep bullets carrying one of `tags`, ordered by tag priority (stable), capped at `limit`."""
    priority = {tag: rank for rank, tag in enumerate(tags)}
    matching = [b for b in bullets if priority.keys() & set(b.get("tags", []))]
    matching.sort(key=lambda b: min(priority[t] for t in b["tags"] if t in priority))
    return [b["text"] for b in matching[:limit]]


def merge_positions(entry, selected):
    """Collapse an entry's positions into one resume entry under the title set in `resume_merge`."""
    merge = entry["resume_merge"]
    return {
        "id": entry["id"],
        "title": merge["title"],
        "date": merge["date"],
        "company": merge["company"],
        "bullets": [bullet for position in selected for bullet in position["bullets"]],
        "used": list(dict.fromkeys(skill for position in selected for skill in position.get("used", []))),
        "note": next((position["note"] for position in selected if position["note"]), None),
        "clients": [],
    }


def site_skill_groups(career):
    """Every skill, grouped in `skill_groups` order, for the website."""
    return [{"label": label, "items": [s["label"] for s in career["skills"] if s["group"] == key]}
            for key, label in career["skill_groups"].items()]


def resume_skills(career, variant, positions):
    """Skills block and per-position tech lines, limited to skills the listed positions actually used."""
    groups = variant["skill_groups"]
    shown = {s["id"]: s for s in career["skills"]
             if s["group"] in groups and s["id"] not in variant.get("exclude_skills", [])}
    every_position = positions + [client for position in positions for client in position["clients"]]
    for position in every_position:
        position["tech"] = [shown[skill]["label"] for skill in position.get("used", [])
                            if skill in shown][:variant["max_tech_per_position"]]
    used = {skill for position in every_position for skill in position.get("used", [])}
    skill_groups = []
    for key in groups:
        items = [s["label"] for s in shown.values() if s["group"] == key and s["id"] in used]
        if items:
            skill_groups.append({"label": career["skill_groups"][key], "items": items})
    return skill_groups


def resume_context(career, variant):
    excluded = set(variant.get("exclude_positions", []))
    notes = variant.get("position_notes", {})
    positions = []
    by_id = {}
    for entry in career["experience"]:
        selected = []
        for position in entry["positions"]:
            if position["id"] in excluded:
                continue
            bullets = select_bullets(position["bullets"], variant["tags"], variant["max_bullets_per_position"])
            if bullets:
                selected.append({**position, "bullets": bullets, "note": notes.get(position["id"]), "clients": []})
        if selected and "resume_merge" in entry:
            selected = [merge_positions(entry, selected)]
        for position in selected:
            parent = by_id.get(position.get("client_of"))
            if parent:
                parent["clients"].append(position)
            else:
                positions.append(position)
                by_id[position["id"]] = position
    certifications = career["certifications"]
    if "certifications" in variant:
        certifications = [cert for cert in certifications if cert["name"] in variant["certifications"]]
    return {
        **career,
        "headline": variant["headline"],
        "availability": variant.get("availability"),
        "summary": career["summaries"][variant["summary"]],
        "positions": positions,
        "certifications": certifications,
        "skill_groups": resume_skills(career, variant, positions),
    }


def count_pdf_pages(path):
    return len(re.findall(rb"/Type\s*/Page(?!s)", path.read_bytes()))


def render_pdfs(jobs):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        for html_path, pdf_path in jobs:
            page.goto(html_path.resolve().as_uri())
            page.pdf(path=str(pdf_path), prefer_css_page_size=True, print_background=True)
        browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-pdf", action="store_true", help="skip PDF rendering")
    args = parser.parse_args()

    career = load_yaml(ROOT / "data" / "career.yaml")
    position_ids = validate_career(career)
    variants = {path.stem: load_yaml(path) for path in sorted((ROOT / "resumes").glob("*.yaml"))}
    for name, variant in variants.items():
        validate_variant(name, variant, career, position_ids)
    site_resume = career["site"]["resume"]
    if site_resume not in variants or not variants[site_resume].get("publish"):
        fail(f"site.resume '{site_resume}' must be a resume variant with publish: true")

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True,
                      undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)

    shutil.rmtree(SITE_DIR, ignore_errors=True)
    shutil.copytree(ROOT / "static", SITE_DIR)
    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "resume").mkdir()

    resume_url = f"resume/{variants[site_resume]['output']}"
    (SITE_DIR / "index.html").write_text(
        env.get_template("site.html.j2").render(**career, resume_url=resume_url, site_skill_groups=site_skill_groups(career),
                                               skill_labels={s["id"]: s["label"] for s in career["skills"]}), encoding="utf-8")
    print(f"site       -> {SITE_DIR / 'index.html'}")

    pdf_jobs = []
    for name, variant in variants.items():
        html_path = RESUME_DIR / Path(variant["output"]).with_suffix(".html").name
        html_path.write_text(env.get_template("resume.html.j2").render(**resume_context(career, variant)),
                             encoding="utf-8")
        pdf_jobs.append((html_path, RESUME_DIR / variant["output"]))

    if args.no_pdf:
        print(f"resumes  -> {RESUME_DIR} (HTML only, --no-pdf)")
        return

    render_pdfs(pdf_jobs)
    for name, variant in variants.items():
        pdf_path = RESUME_DIR / variant["output"]
        pages = count_pdf_pages(pdf_path)
        warning = f"  WARNING: over max_pages={variant['max_pages']}" if pages > variant.get("max_pages", pages) else ""
        print(f"{name:<10} -> {pdf_path} ({pages} page{'s' if pages != 1 else ''}){warning}")
        if variant.get("publish"):
            shutil.copy(pdf_path, SITE_DIR / "resume" / variant["output"])


if __name__ == "__main__":
    main()
