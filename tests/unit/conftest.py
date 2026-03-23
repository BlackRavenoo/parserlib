import pytest

from parserlib.core.exporters import ExporterKind, create_exporter

@pytest.fixture(params=list(ExporterKind))
def exporter(request):
    return create_exporter(request.param)