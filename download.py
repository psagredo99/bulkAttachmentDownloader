#@Author: Pablo Sagredo
#@Email: pablo.sagredo@pkf-attest.es
#@Date: 15/11/2023

import concurrent.futures
from simple_salesforce import Salesforce
import requests
import os.path
import csv
import logging
from alive_progress import alive_bar


def split_into_batches(items, batch_size):
    full_list = list(items)
    for i in range(0, len(full_list), batch_size):
        yield full_list[i:i + batch_size]


def create_filename(title, record_id, parent_id):
    # Create filename
    bad_chars = [';', ':', '!', "*", '/', '\\', ' ', ',','?','>','<']
    clean_title = filter(lambda i: i not in bad_chars, title)
    clean_title = ''.join(list(clean_title))
    
    filename = "{0}-ID-{1}-ParentId-{2}".format(clean_title, record_id, parent_id)
    return filename

    
ATTACHMENT = 'attachment'
NOTE = 'note'


def get_record_ids(sf, output_directory, query, object_type, sharetype='V', visibility='AllUsers'):

    if not os.path.isdir(output_directory):
        os.mkdir(output_directory)

    if object_type == ATTACHMENT:
        results_path = output_directory + 'files.csv'
    elif object_type == NOTE:
        results_path = output_directory + 'content_notes.csv'
    else:
        results_path = output_directory + 'unknown.csv'


    #################-TEST BULK START-##########
    record_ids = set()
    print('########################################################################')
    print('########################################################################')
    print('########################################################################')
    print('\t*LISTADO DE ATTACHMENTS EN PROCESO*\n')
    with alive_bar(spinner="waves") as bar:
        fetch_results = sf.bulk.Attachment.query_all(query, lazy_operation=True)
        bar()
    
    records = []
    for list_results in fetch_results:
        records.extend(list_results)


    # Save results file with file mapping and return ids
    with open(results_path, 'w', encoding='UTF-8', newline='') as results_csv:
        file_writer = csv.writer(results_csv, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        #DEFINIMOS CABECERAS DEL DOCUMENTO
        if object_type == ATTACHMENT:
            file_writer.writerow(
                ['FirstPublishLocationId', 'AttachmentId', 'VersionData', 'PathOnClient', 'Title', 'OwnerId',
                 'CreatedDate', 'CreatedById', 'LastModifiedDate'])
        elif object_type == NOTE:
            file_writer.writerow(
                ['LinkedEntityId', 'LegacyNoteId', 'Title', 'OwnerId', 'Content', 'CreatedDate', 'CreatedById',
                 'LastModifiedDate', 'ShareType', 'Visibility'])
        #ESCRIBIR CADA LINEA
        for content_document in records:
            record_ids.add(content_document["Id"])
            if object_type == ATTACHMENT:
                filename = create_filename(content_document["Name"],
                                           content_document["Id"],
                                           content_document["ParentId"])
                file_writer.writerow(
                    [content_document["ParentId"], content_document["Id"], filename, filename,
                     content_document["Name"], content_document["OwnerId"], content_document['CreatedDate'],
                     content_document['CreatedById'], content_document['LastModifiedDate']])
            elif object_type == NOTE:
                filename = create_filename(content_document["Name"],
                                           content_document["Id"],
                                           content_document["ParentId"])
                file_writer.writerow(
                    [content_document["ParentId"], content_document["Id"], content_document["Title"],
                     content_document["OwnerId"], filename, content_document['CreatedDate'],
                     content_document['CreatedById'], content_document['LastModifiedDate'],
                     sharetype, visibility])

    return record_ids


def download_attachment(args):
    record, output_directory, sf = args
    # Create filename
    filename = create_filename(record["Name"], record["Id"], record["ParentId"])

    url = "https://%s%s%s/body" % (sf.sf_instance, '/services/data/v57.0/sobjects/Attachment/', record["Id"])
    print('#|' +'\U00002705'+ 'RECORD ID -- ' + record["Id"] + ' -- Name -- '+ record["Name"] + ' -- ParentID -- ' + record["ParentId"])

    logging.debug("Downloading from " + url)

    response = requests.get(url, headers={"Authorization": "OAuth " + sf.session_id,
                                          "Content-Type": "application/octet-stream"})

    if response.ok:
        # Save File
        with open(filename, "wb") as output_file:
            output_file.write(response.content)
        return "Saved file to %s" % filename
    else:
        return "Couldn't download %s" % url


def fetch_files(sf, query_string, output_directory, object_type, valid_record_ids=None, batch_size=100):
    # Divide the full list of files into batches of 100 ids to avoid overlaping
    batches = list(split_into_batches(valid_record_ids, batch_size))

    i = 0
    for batch in batches:

        i = i + 1
        logging.info("Processing batch {0}/{1}".format(i, len(batches)))
        batch_query = query_string + ' WHERE Id in (' + ",".join("'" + item + "'" for item in batch) + ')'
        print('########################################################################')
        print('########################################################################')
        print('########################################################################')
        print('\t*DESCARGA DE ARCHIVOS EN PROCESO*\n')

        # MODIFIED
        with alive_bar(spinner="waves") as bar:
            fetch_results = sf.bulk.Attachment.query_all(batch_query, lazy_operation=True)
            bar()
        
        records = []
        for list_results in fetch_results:
            records.extend(list_results)
        #END 

        logging.debug("{0} Query found {1} results".format(object_type, len(records)))

        extracted = 0

        if object_type == ATTACHMENT:
            #MULTI THREADS PARA VARIOS BATCHES
            with concurrent.futures.ProcessPoolExecutor() as executor:
                args = ((record, output_directory, sf) for record in records)
                for result in executor.map(download_attachment, args):
                    logging.debug(result)
        elif object_type == NOTE:
            for r in records:
                filename = create_filename(r["Title"] , r["Id"], r["ParentId"])
                with open(filename, "w") as output_file:
                    extracted += 1
                    if r["Body"]:
                        output_file.write(r["Body"])
                        logging.debug("(%d): Saved blob to %s " % (extracted, filename))
                    else:
                        output_file.write("")
                        logging.debug("(%d): Empty Body for %s" % (extracted, filename))

        logging.info('All files in batch {0} downloaded'.format(i))
    logging.info('All batches complete')


def main():
    import argparse
    import configparser

    parser = argparse.ArgumentParser(description='Export Notes & Attachments from Salesforce')
    parser.add_argument('-q', '--query', metavar='query', required=True,
                        help='SOQL to select records from where Attachments should be downloaded. Must return the '
                             'Id(s) of parent objects.')
    args = parser.parse_args()

    # Get settings from config file
    config = configparser.ConfigParser()
    config.read('download.ini')

    username = config['salesforce']['username']
    password = config['salesforce']['password']
    token = config['salesforce']['security_token']
    is_sandbox = config['salesforce']['connect_to_sandbox']
    download_attachments = config['salesforce']['download_attachments'] == 'True'
    download_notes = config['salesforce']['download_notes'] == 'True'
    batch_size = int(config['salesforce']['batch_size'])
    loglevel = logging.getLevelName(config['salesforce']['loglevel'])
    sharetype = logging.getLevelName(config['salesforce']['sharetype'])
    visibility = logging.getLevelName(config['salesforce']['visibility'])

    print('USERNAME: ' + username)
    print('PASSWORD: ' + password)
    print('SECURITY TOKEN: ' + token)
    print('CONNECT TO SANDBOX: ' + str(is_sandbox))
    print('DOWNLOAD ATTACHMENTS: ' + str(download_attachments))
    print('DOWNLOAD NOTES: ' + str(download_notes))
    print('BATCH SIZE: ' + str(batch_size))

    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=loglevel)

    attachment_query = 'SELECT Id, ContentType, Description, Name, OwnerId, ParentId, CreatedById, CreatedDate, ' \
                       'LastModifiedDate FROM Attachment WHERE ParentId IN ({0})'.format(args.query) 
    
    notes_query = 'SELECT Id, Title, OwnerId, ParentId, CreatedById, CreatedDate, LastModifiedDate ' \
                  'FROM Note WHERE ParentId IN ({0})'.format(args.query)
    output = config['salesforce']['output_dir']

    attachment_query_string = "SELECT Id, ContentType, Description, Name, OwnerId, ParentId FROM Attachment"
    note_query_string = "SELECT Id, Body, Title, OwnerId, ParentId FROM Note"

    domain = None
    if is_sandbox == 'True':
        domain = 'test'

    # Output
    logging.info('Export Attachments from Salesforce')
    logging.info('Username: ' + username)
    logging.info('Output directory: ' + output)

    # Connect
    sf = Salesforce(username=username, password=password, security_token=token, domain=domain)
    logging.debug("Connected successfully to {0}".format(sf.sf_instance))

    if attachment_query and download_attachments:
        logging.info("Querying to get Attachment Ids...")
        valid_record_ids = get_record_ids(sf=sf, output_directory=output, query=attachment_query,
                                          object_type=ATTACHMENT)
        logging.info("Found {0} total attachments".format(len(valid_record_ids)))
        fetch_files(sf=sf, query_string=attachment_query_string, valid_record_ids=valid_record_ids,
                    output_directory=output, object_type=ATTACHMENT, batch_size=batch_size)

    if notes_query and download_notes:
        logging.info("Querying to get Note Ids...")
        valid_record_ids = get_record_ids(sf=sf, output_directory=output, query=notes_query,
                                          object_type=NOTE, sharetype=sharetype, visibility=visibility)
        logging.info("Found {0} total notes".format(len(valid_record_ids)))
        fetch_files(sf=sf, query_string=note_query_string,
                    valid_record_ids=valid_record_ids,
                    output_directory=output, object_type=NOTE, batch_size=batch_size)


if __name__ == "__main__":
    main()
