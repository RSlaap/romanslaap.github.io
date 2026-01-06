# Jobs Directory

This folder contains JSON files for each work experience entry on the website.

## How to Add a New Job

### 1. Create a new JSON file

Create a file named `company-name.json` in this folder. For example: `google.json`

### 2. Add job data

For a **single position**:
```json
{
  "id": "job-5",
  "title": "Software Engineer",
  "date": "2024 - Present",
  "company": "Google, Mountain View",
  "logo": "https://example.com/google-logo.png",
  "responsibilities": [
    "First responsibility",
    "Second responsibility",
    "Third responsibility"
  ]
}
```

For **multiple positions at the same company** (like Nationale Nederlanden):
```json
{
  "id": "job-5",
  "logo": "https://example.com/company-logo.png",
  "positions": [
    {
      "title": "Senior Engineer",
      "date": "2023 - Present",
      "company": "Company Name, Location",
      "responsibilities": [
        "Responsibility 1",
        "Responsibility 2"
      ]
    },
    {
      "title": "Engineer",
      "date": "2021 - 2023",
      "company": "Company Name, Location",
      "responsibilities": [
        "Responsibility 1",
        "Responsibility 2"
      ]
    }
  ]
}
```

### 3. Update jobs-list.json

Add your new file name (without `.json`) to the list in the order you want it to appear:

```json
[
  "ikea",
  "thoughtworks",
  "google",
  "mercedes",
  "mondelez",
  "nn"
]
```

The order in this list determines the order in the carousel (left to right).

### 4. That's it!

The website will automatically load your new job and display it in the carousel and popup.

## Tips

- **ID naming**: Use sequential IDs like `job-0`, `job-1`, `job-2`, etc.
- **Logo URLs**: You can use:
  - URLs from Wikipedia Commons
  - URLs from company websites
  - Local image files (put them in the root folder or a subfolder)
- **Responsibilities**: Keep them concise and action-oriented
- **Dates**: Use formats like "2024 - Present" or "January 2023 - December 2024"

## Editing Existing Jobs

Simply open the corresponding JSON file and edit the data. Changes will appear automatically when you refresh the page.

## Removing a Job

1. Delete the JSON file from this folder
2. Remove the entry from `jobs-list.json`
