### 1. Issue Title: Update Documentation for Project V2 Troubleshooting Link

**Description:**
The documentation is missing a direct link to the new "Project V2 Troubleshooting Guide". The task is to simply add this URL to the main `README.md` file under a clear heading.

**Acceptance Criteria:**
- The correct URL for the Project V2 guide is added to `README.md`.
- The link should be formatted correctly using Markdown.

**Labels:**
`good first issue`, `documentation`, `low-effort`

---

### 2. Issue Title: Add Basic Explanation of Retry/Backoff Strategy

**Description:**
The current project documentation does not clearly explain the basic "retry/backoff" strategy used for API calls. Add a short paragraph (3-4 lines) to the relevant documentation file (`docs/api.md` if it exists, or `README.md`).

**Acceptance Criteria:**
- A clear, simple explanation of retry/backoff is included in the documentation.
- The explanation must be easy for a non-technical user to understand.

**Labels:**
`good first issue`, `documentation`

---

### 3. Issue Title: Fix Typo in Contributor Guide (CONTRIBUTING.md)

**Description:**
There is a minor typo or grammatical error in the `CONTRIBUTING.md` file (e.g., misspelled word or wrong punctuation). The task is to find and fix one such error.

**Acceptance Criteria:**
- One confirmed typo or grammatical error is corrected in the `CONTRIBUTING.md` file.

**Labels:**
`good first issue`, `bug`, `low-effort`

---

### 4. Issue Title: Implement Basic Test for Index Writer Initialization

**Description:**
We need a very simple unit test for the `index_writer` component. The test should only verify that the class/function initializes without raising an exception when given valid (but minimal) input.

**Acceptance Criteria:**
- A new unit test is added to the relevant test file.
- The test ensures the initialization process is successful.

**Labels:**
`good first issue`, `tests`, `python`

---

### 5. Issue Title: Add Sample Structure for JSON Index Schema Doc

**Description:**
To meet the requirement of the original task (#168), create a sample file illustrating the basic structure of the `JSON index schema`. This file should use dummy data.

**Acceptance Criteria:**
- A new file named `sample_index_schema.json` is created in a suitable documentation folder.
- The file contains only the structure (keys/values) with placeholder data.

**Labels:**
`good first issue`, `documentation`, `json`

---

### 6. Issue Title: Review and Update Python Dependency Versions

**Description:**
Check the `requirements.txt` file (or `setup.py`) and ensure that all listed Python libraries have explicit, up-to-date version numbers to prevent unexpected dependency issues.

**Acceptance Criteria:**
- Dependency versions are reviewed and updated where necessary.
- A comment is added to `requirements.txt` stating the date of the review.

**Labels:**
`good first issue`, `dependencies`, `maintenance`

---

### 7. Issue Title: Standardize Code Comment Style in a Single File

**Description:**
Choose one small Python utility file (e.g., `utils.py`) and adjust all existing code comments to follow a uniform style (e.g., ensuring all comments start with a capital letter and end with a period).

**Acceptance Criteria:**
- All comments in the chosen utility file are standardized.
- Only comments are modified; the functional code remains unchanged.

**Labels:**
`good first issue`, `refactoring`, `code-style`

---

### 8. Issue Title: Create New Feature Request Template

**Description:**
Currently, when a user opens a new Issue for a feature request, there is no template. Create a basic Markdown template in the `.github/ISSUE_TEMPLATE` directory to guide users in submitting useful feature requests.

**Acceptance Criteria:**
- A new Markdown template for Feature Requests is created in the correct folder.
- The template should include sections for "Problem," "Proposed Solution," and "Why is this needed."

**Labels:**
`good first issue`, `templates`

---

### 9. Issue Title: Improve Error Message Clarity (Reduction Rules)

**Description:**
Find one instance in the code that handles a failure related to "reduction rules" (as mentioned in #168) and make the error message printed to the console more descriptive and helpful to the end-user.

**Acceptance Criteria:**
- One specific error message related to reduction rules is made clearer.
- The change is minimal and only affects the string content of the error message.

**Labels:**
`good first issue`, `bug`, `ux`

---

### 10. Issue Title: Verify All External Links in Documentation

**Description:**
Check the `docs/` folder for any external hyperlinks (روابط خارجية) and ensure they are all active and not broken (404 error). Fix or remove any broken link found.

**Acceptance Criteria:**
- All external links in the documentation have been checked.
- Any broken link is either updated to the correct URL or removed.

**Labels:**
`good first issue`, `documentation`, `maintenance`

---
