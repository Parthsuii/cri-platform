from __future__ import annotations

import os
import shutil
from pathlib import Path

class RollbackCoordinator:
    def __init__(self, backup_dir: str = ".cri_backups") -> None:
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

    def backup_files(self, checkpoint_id: str, active_files: list[str]) -> dict[str, str]:
        """
        Backs up the specified active files to a unique folder under the checkpoint_id.
        Returns a dictionary mapping original paths to backup paths.
        """
        checkpoint_backup_dir = self.backup_dir / checkpoint_id
        checkpoint_backup_dir.mkdir(exist_ok=True)
        
        backup_map = {}
        for file_path_str in active_files:
            file_path = Path(file_path_str)
            if file_path.exists() and file_path.is_file():
                # Avoid collision by using relative or absolute hash paths
                rel_name = file_path.name
                dest_path = checkpoint_backup_dir / rel_name
                try:
                    shutil.copy2(file_path, dest_path)
                    backup_map[file_path_str] = str(dest_path)
                except Exception as exc:
                    print(f"Failed to backup {file_path_str}: {exc}")
        return backup_map

    def restore_files(self, checkpoint_id: str, backup_map: dict[str, str]) -> list[str]:
        """
        Restores files to their original locations from the backup mapping.
        Returns a list of successfully restored file paths.
        """
        restored = []
        for orig_path_str, backup_path_str in backup_map.items():
            orig_path = Path(orig_path_str)
            backup_path = Path(backup_path_str)
            if backup_path.exists() and backup_path.is_file():
                try:
                    # Ensure directory structure exists
                    orig_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_path, orig_path)
                    restored.append(orig_path_str)
                except Exception as exc:
                    print(f"Failed to restore {orig_path_str}: {exc}")
        return restored

    def clean_checkpoint_backup(self, checkpoint_id: str) -> None:
        checkpoint_backup_dir = self.backup_dir / checkpoint_id
        if checkpoint_backup_dir.exists():
            shutil.rmtree(checkpoint_backup_dir)
