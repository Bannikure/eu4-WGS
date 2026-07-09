"""
Module: External Data Loader
=============================

Handles loading and parsing of external data files (DLL, XML, CCP, JSON, CSV) 
from an 'additional_data' folder.

Supports:
- Dynamic DLL plugin loading (Windows-specific)
- XML configuration parsing
- C++ template serialization
- JSON/YAML configuration files
- Custom binary data formats

This module integrates with the main EU4 generator to override procedural 
defaults with user-provided data.
"""

from __future__ import annotations

import os
import json
import csv
import platform
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# Platform-specific DLL loading
if platform.system() == "Windows":
    import ctypes
    from ctypes import WINFUNCTYPE, c_int, c_char_p
else:
    ctypes = None


class ExternalDataLoader:
    """
    Loads external data files from 'additional_data' folder and provides 
    interfaces for integrating them into mod generation.
    """

    def __init__(self, data_folder: str = "additional_data") -> None:
        """
        Initialize the external data loader.

        Args:
            data_folder: Path to the additional_data directory
        """
        self.data_folder = Path(data_folder)
        self.data_folder.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.subdirs = {
            "dll": self.data_folder / "plugins",
            "xml": self.data_folder / "configs",
            "cpp": self.data_folder / "templates",
            "json": self.data_folder / "data",
            "csv": self.data_folder / "datasets",
            "bin": self.data_folder / "binary",
        }
        
        for subdir in self.subdirs.values():
            subdir.mkdir(exist_ok=True)
        
        # Storage for loaded data
        self.loaded_dll_functions: Dict[str, Callable] = {}
        self.xml_configs: Dict[str, ET.Element] = {}
        self.json_data: Dict[str, Any] = {}
        self.csv_data: Dict[str, List[Dict[str, Any]]] = {}
        self.cpp_templates: Dict[str, str] = {}
        self.binary_data: Dict[str, bytes] = {}
        
        logger.info(f"External Data Loader initialized at: {self.data_folder}")

    # =====================================================================
    #  DLL PLUGIN LOADING (Windows)
    # =====================================================================

    def load_dll_plugins(self, dll_folder: Optional[str] = None) -> Dict[str, Callable]:
        """
        Load DLL plugins from the plugins folder.
        
        Expected DLL interface:
        - Function: 'GenerateCustomTerrain' -> c_int (returns hash or status)
        - Function: 'ModifyProvinces' -> c_int (modifies province data)
        - Function: 'ApplyTradeBonus' -> c_int (applies trade modifiers)
        
        Returns:
            Dictionary mapping function names to callable ctypes functions
        """
        if ctypes is None:
            logger.warning("DLL loading not available on non-Windows platforms")
            return {}
        
        dll_path = dll_folder or self.subdirs["dll"]
        
        if not dll_path.exists():
            logger.warning(f"DLL folder not found: {dll_path}")
            return {}
        
        for dll_file in dll_path.glob("*.dll"):
            try:
                lib = ctypes.CDLL(str(dll_file))
                logger.info(f"Loaded DLL: {dll_file.name}")
                
                # Try to load known functions
                known_functions = [
                    "GenerateCustomTerrain",
                    "ModifyProvinces",
                    "ApplyTradeBonus",
                    "CustomizeReligion",
                    "GenerateTradeNodes",
                ]
                
                for func_name in known_functions:
                    try:
                        func = getattr(lib, func_name)
                        func.argtypes = []
                        func.restype = c_int
                        self.loaded_dll_functions[func_name] = func
                        logger.info(f"  ✓ Loaded function: {func_name}")
                    except AttributeError:
                        pass
                        
            except Exception as e:
                logger.error(f"Failed to load DLL {dll_file.name}: {e}")
        
        return self.loaded_dll_functions

    def call_dll_function(self, function_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Call a loaded DLL function safely with error handling.
        
        Args:
            function_name: Name of the function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result or None if function not found
        """
        if function_name not in self.loaded_dll_functions:
            logger.warning(f"DLL function not found: {function_name}")
            return None
        
        try:
            func = self.loaded_dll_functions[function_name]
            result = func(*args)
            logger.debug(f"DLL function {function_name} returned: {result}")
            return result
        except Exception as e:
            logger.error(f"Error calling DLL function {function_name}: {e}")
            return None

    # =====================================================================
    #  XML CONFIGURATION PARSING
    # =====================================================================

    def load_xml_configs(self, xml_folder: Optional[str] = None) -> Dict[str, ET.Element]:
        """
        Load and parse XML configuration files.
        
        Expected XML structure:
        ```xml
        <eu4_config>
            <map_settings>...</map_settings>
            <trade_nodes>...</trade_nodes>
            <provinces>...</provinces>
        </eu4_config>
        ```
        
        Returns:
            Dictionary mapping filenames to parsed XML ElementTree roots
        """
        xml_path = xml_folder or self.subdirs["xml"]
        
        if not xml_path.exists():
            logger.warning(f"XML folder not found: {xml_path}")
            return {}
        
        for xml_file in xml_path.glob("*.xml"):
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                self.xml_configs[xml_file.stem] = root
                logger.info(f"Loaded XML: {xml_file.name}")
            except ET.ParseError as e:
                logger.error(f"Failed to parse XML {xml_file.name}: {e}")
            except Exception as e:
                logger.error(f"Error loading XML {xml_file.name}: {e}")
        
        return self.xml_configs

    def get_xml_element(self, config_name: str, xpath: str) -> Optional[ET.Element]:
        """
        Extract an element from loaded XML by XPath.
        
        Args:
            config_name: Name of loaded XML config
            xpath: XPath query
            
        Returns:
            Matching Element or None
        """
        if config_name not in self.xml_configs:
            logger.warning(f"XML config not found: {config_name}")
            return None
        
        root = self.xml_configs[config_name]
        try:
            element = root.find(xpath)
            return element
        except Exception as e:
            logger.error(f"XPath query failed: {e}")
            return None

    def get_xml_all(self, config_name: str, xpath: str) -> List[ET.Element]:
        """Get all elements matching XPath."""
        if config_name not in self.xml_configs:
            return []
        
        root = self.xml_configs[config_name]
        try:
            elements = root.findall(xpath)
            return elements
        except Exception as e:
            logger.error(f"XPath query failed: {e}")
            return []

    # =====================================================================
    #  JSON CONFIGURATION LOADING
    # =====================================================================

    def load_json_data(self, json_folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Load JSON configuration and data files.
        
        Expected JSON format:
        ```json
        {
            "provinces": [...],
            "countries": [...],
            "trade_goods": {...}
        }
        ```
        
        Returns:
            Dictionary mapping filenames to parsed JSON data
        """
        json_path = json_folder or self.subdirs["json"]
        
        if not json_path.exists():
            logger.warning(f"JSON folder not found: {json_path}")
            return {}
        
        for json_file in json_path.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.json_data[json_file.stem] = data
                logger.info(f"Loaded JSON: {json_file.name}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON {json_file.name}: {e}")
            except Exception as e:
                logger.error(f"Error loading JSON {json_file.name}: {e}")
        
        return self.json_data

    def get_json_data(self, config_name: str) -> Optional[Any]:
        """Get parsed JSON data by name."""
        return self.json_data.get(config_name)

    # =====================================================================
    #  CSV DATASET LOADING
    # =====================================================================

    def load_csv_datasets(self, csv_folder: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load CSV data files (provinces, trade goods, cultures, etc.).
        
        Expected CSV headers:
        - Provinces: province_id, name, x, y, terrain, culture, religion
        - Trade Goods: good_id, name, base_price, color_r, color_g, color_b
        
        Returns:
            Dictionary mapping filenames to list of row dicts
        """
        csv_path = csv_folder or self.subdirs["csv"]
        
        if not csv_path.exists():
            logger.warning(f"CSV folder not found: {csv_path}")
            return {}
        
        for csv_file in csv_path.glob("*.csv"):
            try:
                with open(csv_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    data = list(reader)
                self.csv_data[csv_file.stem] = data
                logger.info(f"Loaded CSV: {csv_file.name} ({len(data)} rows)")
            except Exception as e:
                logger.error(f"Error loading CSV {csv_file.name}: {e}")
        
        return self.csv_data

    def get_csv_data(self, dataset_name: str) -> Optional[List[Dict[str, Any]]]:
        """Get parsed CSV data by name."""
        return self.csv_data.get(dataset_name)

    # =====================================================================
    #  C++ TEMPLATE SERIALIZATION
    # =====================================================================

    def load_cpp_templates(self, cpp_folder: Optional[str] = None) -> Dict[str, str]:
        """
        Load C++ template files (for advanced procedural generation).
        
        These templates can be used as blueprints for complex generation logic.
        
        Returns:
            Dictionary mapping filenames to template content
        """
        cpp_path = cpp_folder or self.subdirs["cpp"]
        
        if not cpp_path.exists():
            logger.warning(f"C++ template folder not found: {cpp_path}")
            return {}
        
        for cpp_file in cpp_path.glob("*.cpp"):
            try:
                with open(cpp_file, "r", encoding="utf-8") as f:
                    content = f.read()
                self.cpp_templates[cpp_file.stem] = content
                logger.info(f"Loaded C++ template: {cpp_file.name}")
            except Exception as e:
                logger.error(f"Error loading C++ template {cpp_file.name}: {e}")
        
        return self.cpp_templates

    def get_cpp_template(self, template_name: str) -> Optional[str]:
        """Get C++ template content by name."""
        return self.cpp_templates.get(template_name)

    # =====================================================================
    #  BINARY DATA LOADING
    # =====================================================================

    def load_binary_data(self, binary_folder: Optional[str] = None) -> Dict[str, bytes]:
        """
        Load binary data files (.bin, .dat, .custom).
        
        Returns:
            Dictionary mapping filenames to binary content
        """
        binary_path = binary_folder or self.subdirs["bin"]
        
        if not binary_path.exists():
            logger.warning(f"Binary folder not found: {binary_path}")
            return {}
        
        for binary_file in binary_path.glob("*"):
            if binary_file.is_file():
                try:
                    with open(binary_file, "rb") as f:
                        data = f.read()
                    self.binary_data[binary_file.stem] = data
                    logger.info(f"Loaded binary: {binary_file.name} ({len(data)} bytes)")
                except Exception as e:
                    logger.error(f"Error loading binary {binary_file.name}: {e}")
        
        return self.binary_data

    def get_binary_data(self, data_name: str) -> Optional[bytes]:
        """Get binary data by name."""
        return self.binary_data.get(data_name)

    # =====================================================================
    #  DATA INTEGRATION HELPERS
    # =====================================================================

    def load_all(self) -> None:
        """Load all available external data at once."""
        logger.info("Loading all external data...")
        self.load_dll_plugins()
        self.load_xml_configs()
        self.load_json_data()
        self.load_csv_datasets()
        self.load_cpp_templates()
        self.load_binary_data()
        logger.info("External data loading complete")

    def get_province_overrides(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get province data overrides from CSV or JSON.
        
        Returns:
            List of province override dictionaries
        """
        # Try CSV first
        if "provinces" in self.csv_data:
            return self.csv_data["provinces"]
        
        # Try JSON
        if "provinces" in self.json_data:
            return self.json_data.get("provinces", {}).get("data", [])
        
        return None

    def get_trade_goods_overrides(self) -> Optional[Dict[str, Any]]:
        """
        Get trade goods data from external files.
        
        Returns:
            Dictionary of trade goods definitions
        """
        if "trade_goods" in self.csv_data:
            return {"csv": self.csv_data["trade_goods"]}
        
        if "trade_goods" in self.json_data:
            return self.json_data.get("trade_goods", {})
        
        return None

    def get_country_overrides(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get country/nation data overrides.
        
        Returns:
            List of country override dictionaries
        """
        if "countries" in self.csv_data:
            return self.csv_data["countries"]
        
        if "countries" in self.json_data:
            return self.json_data.get("countries", {}).get("data", [])
        
        return None

    def get_map_settings(self) -> Optional[Dict[str, Any]]:
        """
        Get custom map settings from external data.
        
        Returns:
            Dictionary of map settings
        """
        if "map_settings" in self.json_data:
            return self.json_data["map_settings"]
        
        # Try XML
        if "config" in self.xml_configs:
            map_element = self.xml_configs["config"].find("map_settings")
            if map_element is not None:
                return {
                    "width": map_element.findtext("width"),
                    "height": map_element.findtext("height"),
                    "layout": map_element.findtext("layout"),
                }
        
        return None

    def apply_dll_customizations(self, generation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply DLL-based customizations to generated data.
        
        Args:
            generation_data: Generated mod data dictionary
            
        Returns:
            Modified generation data
        """
        if "CustomizeReligion" in self.loaded_dll_functions:
            result = self.call_dll_function("CustomizeReligion")
            if result:
                logger.info("Applied DLL religious customization")
        
        if "GenerateTradeNodes" in self.loaded_dll_functions:
            result = self.call_dll_function("GenerateTradeNodes")
            if result:
                logger.info("Applied DLL trade node generation")
        
        return generation_data

    # =====================================================================
    #  UTILITY METHODS
    # =====================================================================

    def list_available_data(self) -> Dict[str, List[str]]:
        """
        List all available external data by type.
        
        Returns:
            Dictionary mapping data types to list of available items
        """
        return {
            "dll": list(self.loaded_dll_functions.keys()),
            "xml": list(self.xml_configs.keys()),
            "json": list(self.json_data.keys()),
            "csv": list(self.csv_data.keys()),
            "cpp": list(self.cpp_templates.keys()),
            "binary": list(self.binary_data.keys()),
        }

    def validate_data_integrity(self) -> bool:
        """
        Validate loaded data for completeness and consistency.
        
        Returns:
            True if all critical data is present
        """
        validation_passed = True
        
        # Check for required CSV headers
        for dataset_name, rows in self.csv_data.items():
            if not rows:
                logger.warning(f"Empty CSV dataset: {dataset_name}")
                validation_passed = False
        
        # Check for valid JSON structure
        for json_name, data in self.json_data.items():
            if not isinstance(data, (dict, list)):
                logger.warning(f"Invalid JSON structure: {json_name}")
                validation_passed = False
        
        # Check for valid XML roots
        for xml_name, root in self.xml_configs.items():
            if root is None or not isinstance(root, ET.Element):
                logger.warning(f"Invalid XML structure: {xml_name}")
                validation_passed = False
        
        return validation_passed

    def export_summary(self) -> str:
        """
        Generate a summary report of loaded external data.
        
        Returns:
            Formatted summary string
        """
        summary = "\n=== EXTERNAL DATA SUMMARY ===\n"
        summary += f"DLL Functions: {len(self.loaded_dll_functions)}\n"
        summary += f"XML Configs: {len(self.xml_configs)}\n"
        summary += f"JSON Datasets: {len(self.json_data)}\n"
        summary += f"CSV Datasets: {len(self.csv_data)} (total rows: {sum(len(d) for d in self.csv_data.values())})\n"
        summary += f"C++ Templates: {len(self.cpp_templates)}\n"
        summary += f"Binary Files: {len(self.binary_data)}\n"
        summary += "==========================\n"
        return summary


# =====================================================================
#  INTEGRATION WITH EU4GEN MAIN APPLICATION
# =====================================================================

def integrate_external_data_into_generation(
    loader: ExternalDataLoader,
    generation_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge external data into the main generation pipeline.
    
    Args:
        loader: Initialized ExternalDataLoader instance
        generation_data: Generated mod data
        
    Returns:
        Modified generation data with external overrides applied
    """
    logger.info("Integrating external data...")
    
    # Apply province overrides
    province_overrides = loader.get_province_overrides()
    if province_overrides:
        logger.info(f"Applying {len(province_overrides)} province overrides")
        generation_data["province_overrides"] = province_overrides
    
    # Apply trade goods overrides
    trade_overrides = loader.get_trade_goods_overrides()
    if trade_overrides:
        logger.info("Applying trade goods overrides")
        generation_data["trade_goods_overrides"] = trade_overrides
    
    # Apply country overrides
    country_overrides = loader.get_country_overrides()
    if country_overrides:
        logger.info(f"Applying {len(country_overrides)} country overrides")
        generation_data["country_overrides"] = country_overrides
    
    # Apply map settings
    map_settings = loader.get_map_settings()
    if map_settings:
        logger.info("Applying custom map settings")
        generation_data["custom_map_settings"] = map_settings
    
    # Apply DLL customizations
    generation_data = loader.apply_dll_customizations(generation_data)
    
    return generation_data
