"""
AutoGPT File System Tool - File Management

Provides AutoGPT to the agent to work with the file system:
- Creation and editing of files
- Document reading and analysis
- Retaining the results of the work
- Safe work in an isolated directory

Author: Candidate Analysis Team
Version: 1.0.0
"""

import asyncio
import aiofiles
import logging
import json
import csv
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
import shutil
import hashlib

logger = logging.getLogger("file-manager")

class FileSystemTool:
    """
    File system tool
    
    Opportunities:
    - Creation and editing of files
    - Reading different formats
    - Safe work in an isolated directory
    - Backup of important files
    """
    
    def __init__(self, workspace_dir: Union[str, Path]):
        self.workspace = Path(workspace_dir)
        self.workspace.mkdir(exist_ok=True)
        
        # Create a directorial structure
        self.subdirs = {
            "reports": self.workspace / "reports",
            "data": self.workspace / "data", 
            "logs": self.workspace / "logs",
            "temp": self.workspace / "temp",
            "backups": self.workspace / "backups",
            "exports": self.workspace / "exports"
        }
        
        for subdir in self.subdirs.values():
            subdir.mkdir(exist_ok=True)
        
        # File operations statistics
        self.stats = {
            "files_created": 0,
            "files_read": 0,
            "files_updated": 0,
            "files_deleted": 0,
            "total_operations": 0
        }
        
        logger.info(f"📁 File System Tool initialized in {self.workspace}")
    
    async def create_file(self, filename: str, content: str, 
                         subdirectory: str = None) -> Dict[str, Any]:
        'Create a new file'
        try:
            # Determine the path
            if subdirectory and subdirectory in self.subdirs:
                file_path = self.subdirs[subdirectory] / filename
            else:
                file_path = self.workspace / filename
            
            # Validate path safety
            if not self._is_safe_path(file_path):
                raise ValueError(f"Unsafe route: {file_path}")
            
            # Create File
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            # Update statistics
            self.stats["files_created"] += 1
            self.stats["total_operations"] += 1
            
            logger.info(f"📄 File Created: {file_path}")
            
            return {
                "success": True,
                "file_path": str(file_path),
                "size_bytes": len(content.encode('utf-8')),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error of file creation {filename}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def read_file(self, filename: str, subdirectory: str = None) -> Dict[str, Any]:
        'Reading File'
        try:
            # Determine the path
            if subdirectory and subdirectory in self.subdirs:
                file_path = self.subdirs[subdirectory] / filename
            else:
                file_path = self.workspace / filename
            
            # Checking the existence of the file
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Read File
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Update statistics
            self.stats["files_read"] += 1
            self.stats["total_operations"] += 1
            
            logger.info(f"📖 File Read: {file_path}")
            
            return {
                "success": True,
                "content": content,
                "file_path": str(file_path),
                "size_bytes": len(content.encode('utf-8')),
                "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error in reading the file {filename}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_file(self, filename: str, content: str, 
                         subdirectory: str = None, append: bool = False) -> Dict[str, Any]:
        'File Update'
        try:
            # Determine the path
            if subdirectory and subdirectory in self.subdirs:
                file_path = self.subdirs[subdirectory] / filename
            else:
                file_path = self.workspace / filename
            
            # Create a backup copy if a file exists
            if file_path.exists():
                await self._create_backup(file_path)
            
            # Record File
            mode = 'a' if append else 'w'
            async with aiofiles.open(file_path, mode, encoding='utf-8') as f:
                await f.write(content)
            
            # Update statistics
            self.stats["files_updated"] += 1
            self.stats["total_operations"] += 1
            
            logger.info(f"✏️ File updated: {file_path}")
            
            return {
                "success": True,
                "file_path": str(file_path),
                "operation": "append" if append else "overwrite",
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error of file update {filename}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_file(self, filename: str, subdirectory: str = None) -> Dict[str, Any]:
        'File Remove'
        try:
            # Determine the path
            if subdirectory and subdirectory in self.subdirs:
                file_path = self.subdirs[subdirectory] / filename
            else:
                file_path = self.workspace / filename
            
            # Checking the existence of the file
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Create a backup before disposal
            await self._create_backup(file_path)
            
            # Remove File
            file_path.unlink()
            
            # Update statistics
            self.stats["files_deleted"] += 1
            self.stats["total_operations"] += 1
            
            logger.info(f"🗑️ File deleted: {file_path}")
            
            return {
                "success": True,
                "file_path": str(file_path),
                "deleted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error of file removal {filename}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_files(self, subdirectory: str = None, 
                        pattern: str = "*") -> Dict[str, Any]:
        'List of files in the directory'
        try:
            # Defining the directory.
            if subdirectory and subdirectory in self.subdirs:
                target_dir = self.subdirs[subdirectory]
            else:
                target_dir = self.workspace
            
            # Get a file list.
            files = []
            for file_path in target_dir.glob(pattern):
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        "name": file_path.name,
                        "size_bytes": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "extension": file_path.suffix
                    })
            
            # Sorting by date of change
            files.sort(key=lambda x: x["modified"], reverse=True)
            
            logger.info(f"📋 File List: {len(files)} Files in {target_dir}")
            
            return {
                "success": True,
                "directory": str(target_dir),
                "files": files,
                "total_files": len(files)
            }
            
        except Exception as e:
            logger.error(f"❌ Error in obtaining a list of files: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def save_json(self, filename: str, data: Dict[str, Any], 
                       subdirectory: str = "data") -> Dict[str, Any]:
        'Data preservation in JSON'
        try:
            json_content = json.dumps(data, ensure_ascii=False, indent=2)
            return await self.create_file(filename, json_content, subdirectory)
            
        except Exception as e:
            logger.error(f"❌ The JSON Storage Error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def load_json(self, filename: str, subdirectory: str = "data") -> Dict[str, Any]:
        'Loading data from JSON'
        try:
            result = await self.read_file(filename, subdirectory)
            
            if result["success"]:
                data = json.loads(result["content"])
                return {
                    "success": True,
                    "data": data,
                    "file_info": {
                        "file_path": result["file_path"],
                        "size_bytes": result["size_bytes"]
                    }
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"❌ Error of JSON: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def save_csv(self, filename: str, data: List[Dict[str, Any]], 
                      subdirectory: str = "data") -> Dict[str, Any]:
        'Save data to CSV'
        try:
            if not data:
                raise ValueError('No data to save')
            
            # Determine the path
            file_path = self.subdirs[subdirectory] / filename
            
            # Record CSV
            async with aiofiles.open(file_path, 'w', newline='', encoding='utf-8') as f:
                # Getting the headlines from the first entry.
                fieldnames = list(data[0].keys())
                
                # Create CSV contents
                csv_content = []
                
                # Heading
                csv_content.append(','.join(fieldnames))
                
                # Data
                for row in data:
                    values = []
                    for field in fieldnames:
                        value = str(row.get(field, ''))
                        # We'll check the commas and the quotations.
                        if ',' in value or '"' in value or '\n' in value:
                            value = '"' + value.replace('"', '""') + '"'
                        values.append(value)
                    csv_content.append(','.join(values))
                
                await f.write('\n'.join(csv_content))
            
            # Update statistics
            self.stats["files_created"] += 1
            self.stats["total_operations"] += 1
            
            logger.info(f"📊 CSV File Created: {file_path}")
            
            return {
                "success": True,
                "file_path": str(file_path),
                "rows_saved": len(data),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error of CSV: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_report(self, title: str, data: Dict[str, Any], 
                           format_type: str = "markdown") -> Dict[str, Any]:
        'Creating a report in different formats'
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.{format_type}"
            
            if format_type == "markdown":
                content = self._format_markdown_report(title, data)
            elif format_type == "json":
                content = json.dumps({
                    "title": title,
                    "created_at": datetime.now().isoformat(),
                    "data": data
                }, ensure_ascii=False, indent=2)
            else:
                content = self._format_text_report(title, data)
            
            return await self.create_file(filename, content, "reports")
            
        except Exception as e:
            logger.error(f"❌ Error in making a report: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_markdown_report(self, title: str, data: Dict[str, Any]) -> str:
        'Presentation of the report in Markdown'
        report = [
            f"# {title}",
            f"",
            f"** Done:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"---",
            f""
        ]
        
        for key, value in data.items():
            report.append(f"## {key.replace('_', ' ').title()}")
            report.append("")
            
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    report.append(f"- **{subkey}:** {subvalue}")
            elif isinstance(value, list):
                for i, item in enumerate(value, 1):
                    report.append(f"{i}. {item}")
            else:
                report.append(str(value))
            
            report.append("")
        
        return "\n".join(report)
    
    def _format_text_report(self, title: str, data: Dict[str, Any]) -> str:
        'Formatting the report in text format'
        report = [
            "=" * 50,
            title.upper(),
            "=" * 50,
            f"Established: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        for key, value in data.items():
            report.append(f"{key.replace('_', ' ').title()}:")
            report.append("-" * 30)
            
            if isinstance(value, (dict, list)):
                report.append(json.dumps(value, ensure_ascii=False, indent=2))
            else:
                report.append(str(value))
            
            report.append("")
        
        return "\n".join(report)
    
    async def _create_backup(self, file_path: Path) -> None:
        'Create a back-up file'
        try:
            if file_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
                backup_path = self.subdirs["backups"] / backup_name
                
                shutil.copy2(file_path, backup_path)
                logger.debug(f"💾 A backup copy has been created: {backup_path}")
                
        except Exception as e:
            logger.error(f"❌ Error in creating a backup: {e}")
    
    def _is_safe_path(self, file_path: Path) -> bool:
        'Checking route security'
        try:
            # Check that the way is inside the work directorate.
            file_path.resolve().relative_to(self.workspace.resolve())
            return True
        except ValueError:
            return False
    
    async def cleanup_temp_files(self, older_than_hours: int = 24) -> Dict[str, Any]:
        'Cleaning Time Files'
        try:
            cutoff_time = datetime.now().timestamp() - (older_than_hours * 3600)
            deleted_files = []
            
            for file_path in self.subdirs["temp"].iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_files.append(file_path.name)
            
            logger.info(f"🧹 Peeled {len(deleted_files)} Time files")
            
            return {
                "success": True,
                "deleted_files": deleted_files,
                "count": len(deleted_files)
            }
            
        except Exception as e:
            logger.error(f"❌ Error in cleaning temporary files: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_workspace_stats(self) -> Dict[str, Any]:
        'Workspace statistics'
        try:
            stats = {
                "workspace_path": str(self.workspace),
                "subdirectories": {},
                "total_files": 0,
                "total_size_bytes": 0,
                "operations_stats": self.stats
            }
            
            for name, path in self.subdirs.items():
                if path.exists():
                    files = list(path.glob("*"))
                    file_count = len([f for f in files if f.is_file()])
                    size = sum(f.stat().st_size for f in files if f.is_file())
                    
                    stats["subdirectories"][name] = {
                        "file_count": file_count,
                        "size_bytes": size
                    }
                    
                    stats["total_files"] += file_count
                    stats["total_size_bytes"] += size
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error in obtaining statistics: {e}")
            return {"error": str(e)}
