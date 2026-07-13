# =========================================================================
# EU4 World Generator Studio - External Data Loader
# =========================================================================
# Handles loading and parsing of external data files (DLL, XML, JSON, CSV, TXT)

import json
import csv
import ctypes
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import xml.etree.ElementTree as ET

from .constants import ADDITIONAL_DATA_DIR, SUPPORTED_FORMATS

logger = logging.getLogger(__name__)


class ExternalDataLoader:
    """Centralized loader for all external data formats."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the external data loader.
        
        Args:
            data_dir: Directory containing additional data files. Defaults to ADDITIONAL_DATA_DIR.
        """
        self.data_dir = data_dir or ADDITIONAL_DATA_DIR
        self.cache: Dict[str, Any] = {}
        self._ensure_dir_exists()

    def _ensure_dir_exists(self) -> None:
        """Create data directory if it doesn't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Data directory ensured at: {self.data_dir}")

    def load_file(self, filename: str) -> Any:
        """Load any supported file format automatically.
        
        Args:
            filename: Name of the file to load.
            
        Returns:
            Parsed data from the file.
            
        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If file format is not supported.
        """
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Check cache first
        if filename in self.cache:
            logger.debug(f"Loading {filename} from cache")
            return self.cache[filename]
        
        suffix = filepath.suffix.lower()
        
        # Route to appropriate loader
        if suffix == ".json":
            data = self.load_json(filepath)
        elif suffix == ".xml":
            data = self.load_xml(filepath)
        elif suffix == ".csv":
            data = self.load_csv(filepath)
        elif suffix == ".txt":
            data = self.load_txt(filepath)
        elif suffix == ".dll":
            data = self.load_dll(filepath)
        elif suffix in [".dat", ".bin"]:
            data = self.load_binary(filepath)
        elif suffix == ".lua":
            data = self.load_lua(filepath)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
        
        # Cache the result
        self.cache[filename] = data
        logger.info(f"Successfully loaded {filename}")
        return data

    @staticmethod
    def load_json(filepath: Path) -> Dict[str, Any]:
        """Load a JSON file.
        
        Args:
            filepath: Path to JSON file.
            
        Returns:
            Parsed JSON data as dictionary.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filepath}: {e}")
            raise

    @staticmethod
    def load_xml(filepath: Path) -> ET.Element:
        """Load an XML file.
        
        Args:
            filepath: Path to XML file.
            
        Returns:
            Parsed XML root element.
        """
        try:
            tree = ET.parse(filepath)
            return tree.getroot()
        except ET.ParseError as e:
            logger.error(f"Invalid XML in {filepath}: {e}")
            raise

    @staticmethod
    def load_csv(filepath: Path) -> List[Dict[str, str]]:
        """Load a CSV file.
        
        Args:
            filepath: Path to CSV file.
            
        Returns:
            List of dictionaries representing rows.
        """
        try:
            rows = []
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            return rows
        except Exception as e:
            logger.error(f"Error reading CSV {filepath}: {e}")
            raise

    @staticmethod
    def load_txt(filepath: Path) -> Dict[str, Any]:
        """Load a TXT file (EU4 script format).
        
        Args:
            filepath: Path to TXT file.
            
        Returns:
            Parsed script data as dictionary.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse EU4 script format
            parsed = ExternalDataLoader._parse_eu4_script(content)
            return parsed
        except Exception as e:
            logger.error(f"Error reading TXT {filepath}: {e}")
            raise

    @staticmethod
    def load_dll(filepath: Path) -> Dict[str, Any]:
        """Load a DLL file and extract metadata.
        
        Args:
            filepath: Path to DLL file.
            
        Returns:
            Dictionary containing DLL information.
        """
        try:
            # Try to load DLL using ctypes
            dll_data = {
                "path": str(filepath),
                "filename": filepath.name,
                "size": filepath.stat().st_size,
                "type": "DLL",
            }
            
            # Attempt to load and get basic info
            try:
                lib = ctypes.CDLL(str(filepath))
                dll_data["loaded"] = True
                dll_data["functions"] = []
                logger.info(f"Successfully loaded DLL: {filepath.name}")
            except OSError as e:
                dll_data["loaded"] = False
                dll_data["error"] = str(e)
                logger.warning(f"Could not load DLL {filepath.name}: {e}")
            
            return dll_data
        except Exception as e:
            logger.error(f"Error reading DLL {filepath}: {e}")
            raise

    @staticmethod
    def load_binary(filepath: Path) -> bytes:
        """Load a binary file.
        
        Args:
            filepath: Path to binary file.
            
        Returns:
            Raw binary data.
        """
        try:
            with open(filepath, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading binary {filepath}: {e}")
            raise

    @staticmethod
    def load_lua(filepath: Path) -> str:
        """Load a Lua script file.
        
        Args:
            filepath: Path to Lua file.
            
        Returns:
            Lua script content as string.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading Lua {filepath}: {e}")
            raise

    @staticmethod
    def _parse_eu4_script(content: str) -> Dict[str, Any]:
        """Parse EU4 script format (.txt files).
        
        This handles the key = value format used in EU4 scripts.
        
        Args:
            content: Raw script content.
            
        Returns:
            Parsed script data.
        """
        result = {}
        stack = [result]
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Handle nested blocks
            if line.endswith('{'):
                key = line.replace('{', '').strip()
                # Strip an assignment operator so nested keys use their
                # logical name (e.g. "nested = {" -> "nested").
                if '=' in key:
                    key = key.split('=', 1)[0].strip()
                new_dict = {}
                stack[-1][key] = new_dict
                stack.append(new_dict)
            elif line == '}':
                if len(stack) > 1:
                    stack.pop()
            elif '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().rstrip('\t')
                
                # Try to convert to appropriate type
                if value.lower() == 'yes':
                    value = True
                elif value.lower() == 'no':
                    value = False
                elif value.replace('.', '', 1).isdigit():
                    value = float(value) if '.' in value else int(value)
                
                stack[-1][key] = value
        
        return result

    def load_all_from_directory(self, subdirectory: str = "") -> Dict[str, Any]:
        """Load all supported files from a directory.
        
        Args:
            subdirectory: Subdirectory within data_dir to search. Empty string for root.
            
        Returns:
            Dictionary with filename: data pairs.
        """
        search_dir = self.data_dir / subdirectory if subdirectory else self.data_dir
        result = {}
        
        if not search_dir.exists():
            logger.warning(f"Directory not found: {search_dir}")
            return result
        
        for filepath in search_dir.iterdir():
            if filepath.is_file() and filepath.suffix.lower() in self._get_all_extensions():
                try:
                    result[filepath.name] = self.load_file(filepath.name if not subdirectory else f"{subdirectory}/{filepath.name}")
                except Exception as e:
                    logger.error(f"Failed to load {filepath.name}: {e}")
        
        return result

    @staticmethod
    def _get_all_extensions() -> List[str]:
        """Get all supported file extensions.
        
        Returns:
            List of supported extensions.
        """
        extensions = []
        for format_exts in SUPPORTED_FORMATS.values():
            extensions.extend(format_exts)
        return extensions


class ProvinceDataLoader(ExternalDataLoader):
    """Specialized loader for province-related data files."""

    def load_province_definitions(self, filename: str = "province_definitions.csv") -> List[Dict[str, Any]]:
        """Load province definitions from CSV.
        
        Expected format:
        id,name,region,terrain,trade_good,development
        
        Args:
            filename: Name of the definitions file.
            
        Returns:
            List of province definitions.
        """
        data = self.load_csv(self.data_dir / filename)
        
        # Convert numeric fields
        for province in data:
            if 'id' in province:
                province['id'] = int(province['id'])
            if 'development' in province:
                province['development'] = float(province['development'])
        
        return data

    def load_sea_province_data(self, filename: str = "sea_provinces.json") -> List[Dict[str, Any]]:
        """Load sea province data.
        
        Args:
            filename: Name of the sea provinces file.
            
        Returns:
            List of sea province definitions.
        """
        return self.load_json(self.data_dir / filename)

    def load_province_names(self, filename: str = "province_names.txt") -> Dict[int, str]:
        """Load province names from TXT file.
        
        Args:
            filename: Name of the province names file.
            
        Returns:
            Dictionary mapping province IDs to names.
        """
        parsed = self.load_txt(self.data_dir / filename)
        
        # Flatten the parsed structure if needed
        result = {}
        for key, value in parsed.items():
            try:
                result[int(key)] = str(value)
            except (ValueError, TypeError):
                logger.debug("Skipping non-numeric province id key %r in %s", key, filename)
        
        return result


class CountryDataLoader(ExternalDataLoader):
    """Specialized loader for country/nation-related data."""

    def load_custom_countries(self, filename: str = "custom_countries.json") -> List[Dict[str, Any]]:
        """Load custom country definitions.
        
        Args:
            filename: Name of the custom countries file.
            
        Returns:
            List of custom country definitions.
        """
        return self.load_json(self.data_dir / filename)

    def load_country_colors(self, filename: str = "country_colors.txt") -> Dict[str, str]:
        """Load country color definitions.
        
        Args:
            filename: Name of the country colors file.
            
        Returns:
            Dictionary mapping country tags to RGB colors.
        """
        return self.load_txt(self.data_dir / filename)


class EconomyDataLoader(ExternalDataLoader):
    """Specialized loader for economic data."""

    def load_trade_goods(self, filename: str = "trade_goods.csv") -> List[Dict[str, Any]]:
        """Load trade goods definitions.
        
        Args:
            filename: Name of the trade goods file.
            
        Returns:
            List of trade goods with properties.
        """
        return self.load_csv(self.data_dir / filename)

    def load_trade_nodes(self, filename: str = "trade_nodes.json") -> Dict[str, Any]:
        """Load trade node definitions.
        
        Args:
            filename: Name of the trade nodes file.
            
        Returns:
            Dictionary of trade nodes and their properties.
        """
        return self.load_json(self.data_dir / filename)

    def load_trade_routes(self, filename: str = "trade_routes.xml") -> ET.Element:
        """Load trade routes from XML.
        
        Args:
            filename: Name of the trade routes file.
            
        Returns:
            XML element tree of trade routes.
        """
        return self.load_xml(self.data_dir / filename)


class ReligionCultureDataLoader(ExternalDataLoader):
    """Specialized loader for religion and culture data."""

    def load_religions(self, filename: str = "religions.json") -> Dict[str, Any]:
        """Load religion definitions.
        
        Args:
            filename: Name of the religions file.
            
        Returns:
            Dictionary of religion definitions.
        """
        return self.load_json(self.data_dir / filename)

    def load_cultures(self, filename: str = "cultures.csv") -> List[Dict[str, str]]:
        """Load culture definitions.
        
        Args:
            filename: Name of the cultures file.
            
        Returns:
            List of culture definitions.
        """
        return self.load_csv(self.data_dir / filename)


def create_sample_data_files() -> None:
    """Create sample data files for testing.
    
    This generates example files in the additional_data directory.
    """
    # Sample trade goods
    sample_trade_goods = [
        {"name": "grain", "price": 1.0, "regions": "plains,grassland"},
        {"name": "spices", "price": 3.0, "regions": "tropical"},
        {"name": "gold", "price": 4.0, "regions": "mountains"},
    ]
    
    trade_goods_path = ADDITIONAL_DATA_DIR / "trade_goods.csv"
    if not trade_goods_path.exists():
        with open(trade_goods_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["name", "price", "regions"])
            writer.writeheader()
            writer.writerows(sample_trade_goods)
        logger.info(f"Created sample file: {trade_goods_path}")
    
    # Sample provinces
    sample_provinces = {
        "1": "Capital",
        "2": "Northern Plains",
        "3": "Mountain Pass",
    }
    
    provinces_path = ADDITIONAL_DATA_DIR / "province_names.txt"
    if not provinces_path.exists():
        with open(provinces_path, 'w', encoding='utf-8') as f:
            for prov_id, name in sample_provinces.items():
                f.write(f"{prov_id} = {name}\n")
        logger.info(f"Created sample file: {provinces_path}")
