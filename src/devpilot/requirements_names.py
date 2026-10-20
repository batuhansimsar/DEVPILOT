"""Recognize common pip requirements manifest filenames without reading content."""


def is_requirements_manifest(name: str) -> bool:
    """Accept pip and pip-tools filenames in both common naming orders.

    Besides requirements.txt and requirements-dev.in, projects often use
    dev-requirements.txt or test-requirements.in. Do not mistake unrelated
    sources, Markdown files, or suffix-only names for dependency manifests.
    """
    return name.endswith(('.txt', '.in')) and (
        name.startswith('requirements') or name.endswith(('-requirements.txt', '-requirements.in'))
    )
