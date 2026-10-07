import shutil
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


@dataclass(frozen=True)
class JobWorkspace:
    """Chemins locaux déterministes, indépendants du nom de l'utilisateur."""

    root: Path

    @property
    def source_dir(self):
        return self.root / 'source'

    @property
    def working_dir(self):
        return self.root / 'working'

    @property
    def output_dir(self):
        return self.root / 'output'


def workspace_for(job):
    return JobWorkspace(Path(settings.MEDIA_ROOT) / 'jobs' / str(job.pk))


def prepare_source(job, workspace):
    """Copier la source sans déplacer l'upload ni réutiliser un workspace existant."""
    workspace.root.mkdir(parents=True, exist_ok=False)
    for folder in (workspace.source_dir, workspace.working_dir, workspace.output_dir):
        folder.mkdir()
    source = job.source.button_televerse
    path = workspace.source_dir / ('source' + Path(source.name).suffix)
    with source.open('rb') as original, path.open('xb') as copy:
        shutil.copyfileobj(original, copy)
    return str(path)
