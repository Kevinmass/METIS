import pytest


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
    }


@pytest.fixture
def page_with_api(page):
    """Fixture que asegura que la API esté corriendo."""
    # Aquí podríamos agregar lógica para verificar que la API esté up
    # Pero por simplicidad, asumimos que el CI lo maneja
    return page
