from unidiff import PatchSet
import io
from dbt_reviewer.models import ChangedFile, DiffHunk


def parse_diff(diff_text: str) -> list[ChangedFile]:
    patch = PatchSet(io.StringIO(diff_text))
    changed_files = []
    for patched_file in patch:
        path = patched_file.path
        if not path.endswith('.sql'):
            continue
        model_name = path.split('/')[-1].replace('.sql', '')
        is_new_file = patched_file.is_added_file
        added_lines = []
        hunks = []
        for hunk in patched_file:
            hunk_lines = []
            for line in hunk:
                if line.is_added:
                    added_lines.append(line.value.rstrip('\n'))
                    hunk_lines.append(line.value.rstrip('\n'))
            if hunk_lines:
                hunks.append(DiffHunk(
                    start_line=hunk.target_start,
                    content='\n'.join(hunk_lines)
                ))
        changed_files.append(ChangedFile(
            path=path,
            model_name=model_name,
            is_sql=True,
            is_new_file=is_new_file,
            added_lines=added_lines,
            hunks=hunks,
        ))
    return changed_files
