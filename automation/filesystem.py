"""File and folder automation for the WEBS application.

Capabilities:
- File operations (create, delete, copy, move, rename)
- Content operations (read, write)
- Archive operations (compress, extract)
- Search operations

Consistently uses pathlib.Path for all path operations.
"""

import os
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import List, Optional

from .exceptions import FileSystemAutomationError


class FilesystemAutomation:
    """File system operations automation."""

    # ============= FILE CREATION & DELETION =============

    def create_file(self, path: str, content: str = "") -> None:
        """Create a new file.
        
        Args:
            path: Path to the file.
            content: Optional file content.
            
        Raises:
            FileSystemAutomationError: If file creation fails.
        """
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
        except Exception as e:
            raise FileSystemAutomationError(f"Failed to create file {path}: {e}")

    def delete_file(self, path: str) -> None:
        """Delete a file.
        
        Args:
            path: Path to the file.
            
        Raises:
            FileSystemAutomationError: If file deletion fails.
        """
        try:
            os.remove(path)
        except Exception as e:
            raise FileSystemAutomationError(f"Failed to delete file {path}: {e}")

    # ============= DIRECTORY OPERATIONS =============

    def create_directory(self, path: str) -> None:
        """Create a directory.
        
        Args:
            path: Path to the directory.
            
        Raises:
            FileSystemAutomationError: If directory creation fails.
        """
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise FileSystemAutomationError(f"Failed to create directory {path}: {e}")

    def delete_directory(self, path: str, recursive: bool = True) -> None:
        """Delete a directory.
        
        Args:
            path: Path to the directory.
            recursive: Whether to delete recursively.
            
        Raises:
            FileSystemAutomationError: If directory deletion fails.
        """
        try:
            if recursive:
                shutil.rmtree(path)
            else:
                os.rmdir(path)
        except Exception as e:
            raise FileSystemAutomationError(f"Failed to delete directory {path}: {e}")

    def list_files(self, path: str) -> List[str]:
        """List files in a directory.
        
        Args:
            path: Path to the directory.
            
        Returns:
            List of file names.
            
        Raises:
            FileSystemAutomationError: If listing fails.
        """
        try:
            return os.listdir(path)
        except Exception as e:
            raise FileSystemAutomationError(f"Failed to list files in {path}: {e}")

    # ============= FILE OPERATIONS =============

    def copy(self, src: str, dst: str) -> None:
        """Copy a file.
        
        Args:
            src: Source file path.
            dst: Destination file path.
            
        Raises:
            FileSystemAutomationError: If copy fails.
        """
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            raise FileSystemAutomationError(f"Failed to copy {src} to {dst}: {e}")

    def move(self, src: str, dst: str) -> None:
        """Move a file or directory.
        
        Args:
            src: Source path.
            dst: Destination path.
            
        Raises:
            FileSystemAutomationError: If move fails.
        """
        try:
            shutil.move(src, dst)
        except Exception as e:
            raise FileSystemAutomationError(f"Failed to move {src} to {dst}: {e}")

    def rename(self, path: str, new_name: str) -> None:
        """Rename a file or directory.
        
        Args:
            path: Current path.
            new_name: New name (not a full path).
            
        Raises:
            FileSystemAutomationError: If rename fails.
        """
        try:
            parent = Path(path).parent
            new_path = parent / new_name
            os.rename(path, str(new_path))
        except Exception as e:
            raise FileSystemAutomationError(f"Failed to rename {path}: {e}")

    # ============= CONTENT OPERATIONS =============

    def read(self, path: str) -> str:
        """Read file contents.
        
        Args:
            path: Path to the file.
            
        Returns:
            File contents as string.
            
        Raises:
            FileSystemAutomationError: If read fails.
        """
        try:
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            raise FileSystemAutomationError(f"Failed to read file {path}: {e}")

    def write(self, path: str, content: str, append: bool = False) -> None:
        """Write content to a file.
        
        Args:
            path: Path to the file.
            content: Content to write.
            append: Whether to append (True) or overwrite (False).
            
        Raises:
            FileSystemAutomationError: If write fails.
        """
        try:
            mode = "a" if append else "w"
            with open(path, mode) as f:
                f.write(content)
        except Exception as e:
            raise FileSystemAutomationError(f"Failed to write to file {path}: {e}")

    # ============= ARCHIVE OPERATIONS =============

    def compress(self, source: str, destination: str, format: str = "zip") -> None:
        """Compress files or directories.
        
        Args:
            source: Path to file or directory to compress.
            destination: Output archive path.
            format: Archive format ("zip" or "tar").
            
        Raises:
            FileSystemAutomationError: If compression fails.
        """
        try:
            if format == "zip":
                shutil.make_archive(
                    destination.replace(".zip", ""),
                    "zip",
                    source,
                )
            elif format == "tar":
                with tarfile.open(destination, "w:gz") as tar:
                    tar.add(source, arcname=os.path.basename(source))
            else:
                raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            raise FileSystemAutomationError(
                f"Failed to compress {source}: {e}"
            )

    def extract(self, archive: str, destination: str) -> None:
        """Extract archive files.
        
        Args:
            archive: Path to the archive file.
            destination: Directory to extract to.
            
        Raises:
            FileSystemAutomationError: If extraction fails.
        """
        try:
            if archive.endswith(".zip"):
                with zipfile.ZipFile(archive, "r") as zip_ref:
                    zip_ref.extractall(destination)
            elif archive.endswith(".tar.gz") or archive.endswith(".tgz"):
                with tarfile.open(archive, "r:gz") as tar:
                    tar.extractall(destination)
            else:
                raise ValueError(f"Unsupported archive format: {archive}")
        except Exception as e:
            raise FileSystemAutomationError(f"Failed to extract {archive}: {e}")

    # ============= UTILITY OPERATIONS =============

    def exists(self, path: str) -> bool:
        """Check if a path exists.
        
        Args:
            path: Path to check.
            
        Returns:
            True if path exists, False otherwise.
        """
        return os.path.exists(path)

    def is_file(self, path: str) -> bool:
        """Check if path is a file.
        
        Args:
            path: Path to check.
            
        Returns:
            True if path is a file, False otherwise.
        """
        return os.path.isfile(path)

    def is_directory(self, path: str) -> bool:
        """Check if path is a directory.
        
        Args:
            path: Path to check.
            
        Returns:
            True if path is a directory, False otherwise.
        """
        return os.path.isdir(path)

    def search(self, directory: str, pattern: str) -> List[str]:
        """Search for files matching a pattern.
        
        Args:
            directory: Directory to search in.
            pattern: File name pattern (supports * and ?).
            
        Returns:
            List of matching file paths.
            
        Raises:
            FileSystemAutomationError: If search fails.
        """
        try:
            import fnmatch
            
            matches = []
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    if fnmatch.fnmatch(filename, pattern):
                        matches.append(os.path.join(root, filename))
            return matches
        except Exception as e:
            raise FileSystemAutomationError(f"Failed to search in {directory}: {e}")
