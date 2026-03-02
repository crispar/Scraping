import threading
from typing import Callable
from crawler.services.crawler_service import CrawlerService


class MainViewModel:
    """
    ViewModel for the main application window.
    Handles state management and communication between the View and the Service.
    """

    def __init__(self):
        self._service = CrawlerService()
        self._lock = threading.Lock()

        # State variables
        self.url = ""
        self.status_message = "Ready to extract content"
        self.is_extracting = False
        self.result_text = ""
        self.platform_detected = ""
        self.extraction_success = False

        # Callbacks (to be bound by the View)
        self.on_property_changed: Callable[[str], None] = lambda prop: None
        self.on_extraction_finished: Callable[[bool], None] = lambda success: None

    def start_extraction(self, url: str):
        """Initiates the extraction process in a separate thread."""
        if self.is_extracting:
            return

        self.url = url.strip()
        if not self.url:
            return

        self.is_extracting = True
        self.status_message = "Starting extraction..."
        self._notify_property_changed('is_extracting')
        self._notify_property_changed('status_message')

        thread = threading.Thread(target=self._process_extraction)
        thread.daemon = True
        thread.start()

    def _process_extraction(self):
        """Background process for extraction."""
        try:
            platform_detected = self._service.detect_platform(self.url)
            with self._lock:
                self.platform_detected = platform_detected
                self.status_message = f"Detected platform: {platform_detected}"
            self._notify_property_changed('status_message')

            with self._lock:
                self.status_message = "Extracting content..."
            self._notify_property_changed('status_message')

            result = self._service.extract_content(self.url)

            with self._lock:
                self.extraction_success = result.success
                self.status_message = result.message
                self.result_text = result.formatted_text
                self.is_extracting = False

            self._notify_property_changed('result_text')
            self._notify_property_changed('status_message')
            self._notify_property_changed('is_extracting')

            if self.on_extraction_finished:
                self.on_extraction_finished(result.success)

        except Exception as e:
            with self._lock:
                self.extraction_success = False
                self.status_message = f"Error: {str(e)}"
                self.is_extracting = False

            self._notify_property_changed('status_message')
            self._notify_property_changed('is_extracting')

            if self.on_extraction_finished:
                self.on_extraction_finished(False)

    def _notify_property_changed(self, property_name: str):
        if self.on_property_changed:
            self.on_property_changed(property_name)
