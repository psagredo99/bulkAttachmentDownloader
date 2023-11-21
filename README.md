# Bulk Attachment Downloader


Bulk Attachment Downloader is a Python script that utilizes Salesforce Bulk API to efficiently download attachments and notes based on SOQL queries. This tool is designed to streamline the process of exporting attachments and notes from Salesforce.

![Preview](https://github.com/psagredo99/bulkAttachmentDownloader/assets/72439144/e56c56fb-3987-4d1c-966e-015be401f0d3)

## Features

- Downloads attachments and notes from Salesforce based on specified SOQL queries.
- Utilizes Salesforce Bulk API for efficient and bulk data retrieval.
- Supports parallel processing using multi-threading for improved performance.
- Outputs files with informative filenames for easy identification.

![Preview](https://github.com/psagredo99/bulkAttachmentDownloader/assets/72439144/6cdba01b-4ed5-4d17-bf64-e657be20b452)

## Usage

1. **Clone the repository:**

   ```bash
   git clone https://github.com/psagredo99/bulkAttachmentDownloader.git
   cd bulkAttachmentDownloader
2. **Install requirements:**

   ```bash
   pip install -r requirements.txt
3. **Configure Salesforce credentials and settings in download.ini:**
   ```bash
   [salesforce]
   username = YOUR_SALESFORCE_USERNAME
   password = YOUR_SALESFORCE_PASSWORD
   security_token = YOUR_SECURITY_TOKEN
   connect_to_sandbox = True  # Set to False for production
   download_attachments = True
   download_notes = True
   batch_size = 100 #Care for big amount of attachments as SF will timeout F.E. 10k batch size
   loglevel = INFO
   sharetype = YOUR_SHARE_TYPE
   visibility = YOUR_VISIBILITY

4. **Run script (Example query):**
   -Query must retrieve parent ids of attachments.
   ```bash
   python download.py -q "SELECT id FROM EmailMessage WHERE HasAttachment = true"
   

## Author

   **Author**: Pablo Sagredo
   **Email**: pablo.sagredo@pkf-attest.es
   **Date**: 15/11/2023
