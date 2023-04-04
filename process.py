import os
import json
from typing import Iterator, Optional, Sequence, Tuple
from google.cloud import storage
import google.cloud.documentai_v1 as docai
from tabulate import tabulate

PROJECT_ID = "infra-devops-activities"
API_LOCATION = "us" 

assert PROJECT_ID, "PROJECT_ID is undefined"
assert API_LOCATION in ("us", "eu"), "API_LOCATION is incorrect"

strclient = storage.Client(project='infra-devops-activities')
bucket = strclient.get_bucket('iso-mount')

# Test processors
document_ocr_display_name = "document-ocr"
form_parser_display_name = "form-parser"

test_processor_display_names_and_types = (
    (document_ocr_display_name, "OCR_PROCESSOR"),
    (form_parser_display_name, "FORM_PARSER_PROCESSOR"),
)


def get_client() -> docai.DocumentProcessorServiceClient:
    client_options = {"api_endpoint": f"{API_LOCATION}-documentai.googleapis.com"}
    return docai.DocumentProcessorServiceClient(client_options=client_options)


def get_parent(client: docai.DocumentProcessorServiceClient) -> str:
    return client.common_location_path(PROJECT_ID, API_LOCATION)


def get_client_and_parent() -> Tuple[docai.DocumentProcessorServiceClient, str]:
    client = get_client()
    parent = get_parent(client)
    return client, parent


def fetch_processor_types() -> Sequence[docai.ProcessorType]:
    client, parent = get_client_and_parent()
    response = client.fetch_processor_types(parent=parent)

    return response.processor_types


def print_processor_types(processor_types: Sequence[docai.ProcessorType]):
    def sort_key(pt):
        return (not pt.allow_creation, pt.category, pt.type_)

    sorted_processor_types = sorted(processor_types, key=sort_key)
    data = processor_type_tabular_data(sorted_processor_types)
    headers = next(data)
    colalign = next(data)

    print(tabulate(data, headers, tablefmt="pretty", colalign=colalign))
    print(f"→ Processor types: {len(sorted_processor_types)}")


def processor_type_tabular_data(
    processor_types: Sequence[docai.ProcessorType],
) -> Iterator[Tuple[str, str, str, str]]:
    def locations(pt):
        return ", ".join(sorted(loc.location_id for loc in pt.available_locations))

    yield ("type", "category", "allow_creation", "locations")
    yield ("left", "left", "left", "left")
    if not processor_types:
        yield ("-", "-", "-", "-")
        return
    for pt in processor_types:
        yield (pt.type_, pt.category, f"{pt.allow_creation}", locations(pt))

processor_types = fetch_processor_types()

def list_processors() -> Sequence[docai.Processor]:
    client, parent = get_client_and_parent()
    response = client.list_processors(parent=parent)

    return response.processors


def print_processors(processors: Optional[Sequence[docai.Processor]] = None):
    def sort_key(processor):
        return processor.display_name

    if processors is None:
        processors = list_processors()
    sorted_processors = sorted(processors, key=sort_key)
    data = processor_tabular_data(sorted_processors)
    headers = next(data)
    colalign = next(data)

    print(tabulate(data, headers, tablefmt="pretty", colalign=colalign))
    print(f"→ Processors: {len(sorted_processors)}")


def processor_tabular_data(
    processors: Sequence[docai.Processor],
) -> Iterator[Tuple[str, str, str]]:
    yield ("display_name", "type", "state")
    yield ("left", "left", "left")
    if not processors:
        yield ("-", "-", "-")
        return
    for processor in processors:
        yield (processor.display_name, processor.type_, processor.state.name)

processors = list_processors()

def get_processor(
    display_name: str,
    processors: Optional[Sequence[docai.Processor]] = None,
) -> Optional[docai.Processor]:
    if processors is None:
        processors = list_processors()
    for processor in processors:
        if processor.display_name == display_name:
            return processor
    return None
    


def process_file(
    processor: docai.Processor,
    file_path: str,
    mime_type: str,
) -> docai.Document:
    client = get_client()
    with open(file_path, "rb") as document_file:
        document_content = document_file.read()
    document = docai.RawDocument(content=document_content, mime_type=mime_type)
    request = docai.ProcessRequest(raw_document=document, name=processor.name)

    response = client.process_document(request)

    return response.document

processor = get_processor(form_parser_display_name)
assert processor is not None

#file_path = "/tmp/form.pdf"
file_env = os.environ.get('FILEENV')
file_path = f"/tmp/{file_env}"
mime_type = "application/pdf"

document = process_file(processor, file_path, mime_type)
#here you do changes on parsing like how you want to display data
fnltxt = document.text.split("\n")
json_string = json.dumps(fnltxt)
data = json_string.encode('utf-8')

blob1 = bucket.blob(f'{file_env}ocroutput.json')
blob1.upload_from_string(data)
