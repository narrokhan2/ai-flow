import requests

from ..node_config_builder import FieldBuilder, NodeConfigBuilder

from ....utils.processor_utils import (
    create_temp_file_with_bytes_content,
    get_max_file_size_in_mb,
    is_accepted_url_file_size,
    is_s3_file,
    is_valid_url,
)
from ..model import Field, NodeConfig
from .extension_processor import BasicExtensionProcessor
from langchain.document_loaders import (
    UnstructuredPDFLoader,
    UnstructuredHTMLLoader,
    CSVLoader,
    JSONLoader,
    TextLoader,
)


class DocumentToText(BasicExtensionProcessor):
    processor_type = "document-to-text-processor"

    def __init__(self, config):
        super().__init__(config)
        self.loaders = {
            "application/pdf": UnstructuredPDFLoader,
            "text/plain": TextLoader,
            "text/csv": CSVLoader,
            "text/html": UnstructuredHTMLLoader,
            "application/json": JSONLoader,
        }
        self.accepted_mime_types = self.loaders.keys()

    def get_node_config(self) -> NodeConfig:
        urlField = (
            FieldBuilder()
            .set_name("document_url")
            .set_label("document_url")
            .set_type("textfield")
            .set_required(True)
            .set_placeholder("URLPlaceholder")
            .set_has_handle(True)
            .build()
        )

        return (
            NodeConfigBuilder()
            .set_node_name("DocumentToText")
            .set_processor_type(self.processor_type)
            .set_icon("FaFile")
            .set_section("tools")
            .set_help_message("documentToTextHelp")
            .set_show_handles(True)
            .set_output_type("text")
            .add_field(urlField)
            .build()
        )

    def get_loader_for_mime_type(self, mime_type, path):
        """Return an instance of the loader class associated with the given mime_type."""
        loader_class = self.loaders.get(mime_type)
        if loader_class:
            return loader_class(file_path=path)
        else:
            return None

    def process(self):
        url = self.get_input_by_name("document_url")

        if not is_valid_url(url):
            raise ValueError("Invalid URL")

        if not is_s3_file(url) and not is_accepted_url_file_size(url):
            raise ValueError(
                f"File size is too large (Max : {get_max_file_size_in_mb()})"
            )

        r = requests.get(url)
        if r.status_code != 200:
            raise ValueError(
                "Check the url of your file; returned status code %s" % r.status_code
            )

        mime_type = r.headers.get("Content-Type")
        if not is_s3_file(url) and mime_type not in self.accepted_mime_types:
            raise ValueError("The file type is not supported.")

        temp_file, temp_dir = create_temp_file_with_bytes_content(r.content)
        file_path = str(temp_file)

        loader = self.get_loader_for_mime_type(mime_type, file_path)
        try:
            document = loader.load()
            if len(document) > 0:
                output = document[0].page_content
                return output
            else:
                return None
        except Exception as e:
            print(f"Failed to load document from URL: {e}")
            return None
        finally:
            temp_dir.cleanup()
