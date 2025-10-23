# import frappe
# from frappe import _ as _t

# # reuse your existing mapper if available
# try:
#     from farmportal.api.requests import _get_party_from_user
# except Exception:
#     def _get_party_from_user(user):
#         return None, None

# @frappe.whitelist()
# def begin_import():
#     """Create a Land Plot Import doc (Draft) linked to logged-in supplier and return its name."""
#     user = frappe.session.user
#     if user == "Guest":
#         frappe.throw(_t("Not logged in"), frappe.PermissionError)

#     customer, supplier = _get_party_from_user(user)
#     if not supplier:
#         frappe.throw(_t("Only Suppliers can upload"), frappe.PermissionError)

#     doc = frappe.get_doc({
#         "doctype": "Land Plot Import",
#         "supplier": supplier,
#         "status": "Draft",
#     })
#     doc.insert(ignore_permissions=True)
#     frappe.db.commit()
#     return {"name": doc.name}

# @frappe.whitelist()
# def finalize_import(name: str, total_plots: int = 0, log: str | None = None, status: str | None = None):
#     """Mark an import as Imported (or Failed) and store counts/log."""
#     doc = frappe.get_doc("Land Plot Import", name)
#     doc.total_plots = int(total_plots or 0)
#     if status and status in {"Draft", "Imported", "Failed"}:
#         doc.status = status
#     else:
#         doc.status = "Imported"
#     if log is not None:
#         doc.log = log
#     doc.save(ignore_permissions=True)
#     frappe.db.commit()
#     return {"ok": True, "name": name, "file_url": doc.source_file}
# import frappe
# import json
# from frappe import _

# # Helper function to get supplier from user
# def _get_party_from_user(user):
#     """Get supplier from user - adjust this based on your app structure"""
#     # You may need to adjust this logic based on how suppliers are linked to users in your app
#     supplier_list = frappe.get_all("Supplier", 
#         filters={"custom_user": user}, 
#         fields=["name"]
#     )
#     if supplier_list:
#         return None, supplier_list[0].name
#     return None, None

# @frappe.whitelist()
# def get_land_plots():
#     """Get all land plots for the logged-in supplier"""
#     user = frappe.session.user
#     if user == "Guest":
#         frappe.throw(_("Not logged in"), frappe.PermissionError)

#     customer, supplier = _get_party_from_user(user)
#     if not supplier:
#         frappe.throw(_("Only Suppliers can access land plots"), frappe.PermissionError)

#     plots = frappe.get_all("Land Plot", 
#         filters={"supplier": supplier},
#         fields=[
#             "name", "plot_id", "plot_name", "country", "area", 
#             "coordinates", "geojson", "latitude", "longitude",
#             "commodities", "deforestation_percentage", "deforested_area",
#             "deforested_polygons"
#         ]
#     )
    
#     # Parse JSON fields and add products
#     for plot in plots:
#         try:
#             if plot.coordinates:
#                 plot.coordinates = json.loads(plot.coordinates)
#             if plot.geojson:
#                 plot.geojson = json.loads(plot.geojson)
#             if plot.deforested_polygons:
#                 plot.deforested_polygons = json.loads(plot.deforested_polygons)
#         except:
#             pass
            
#         # Get products
#         products = frappe.get_all("Land Plot Product",
#             filters={"parent": plot.name},
#             fields=["product", "product_name"]
#         )
#         plot.products = [p.product for p in products]
        
#         # Parse commodities 
#         if plot.commodities:
#             plot.commodities = [c.strip() for c in plot.commodities.split(',')]
#         else:
#             plot.commodities = []
    
#     return {"data": plots}

# @frappe.whitelist()
# def create_land_plot(plot_data):
#     """Create a new land plot"""
#     user = frappe.session.user
#     if user == "Guest":
#         frappe.throw(_("Not logged in"), frappe.PermissionError)

#     customer, supplier = _get_party_from_user(user)
#     if not supplier:
#         frappe.throw(_("Only Suppliers can create land plots"), frappe.PermissionError)

#     data = json.loads(plot_data) if isinstance(plot_data, str) else plot_data
    
#     # Create the main document
#     doc = frappe.get_doc({
#         "doctype": "Land Plot",
#         "plot_id": data.get("id") or data.get("plot_id"),
#         "plot_name": data.get("name") or data.get("plot_name"),
#         "supplier": supplier,
#         "country": data.get("country"),
#         "area": data.get("area", 0),
#         "coordinates": json.dumps(data.get("coordinates", [])) if data.get("coordinates") else None,
#         "geojson": json.dumps(data.get("geojson")) if data.get("geojson") else None,
#         "latitude": data.get("latitude"),
#         "longitude": data.get("longitude"),
#         "commodities": ",".join(data.get("commodities", [])),
#         "deforestation_percentage": data.get("deforestationData", {}).get("percentage", 0),
#         "deforested_area": data.get("deforestationData", {}).get("deforestedArea", 0),
#         "deforested_polygons": json.dumps(data.get("deforestationData", {}).get("deforestedPolygons")) if data.get("deforestationData", {}).get("deforestedPolygons") else None
#     })
    
#     # Add products
#     for product_id in data.get("products", []):
#         doc.append("products", {
#             "product": product_id
#         })
    
#     doc.insert(ignore_permissions=True)
#     frappe.db.commit()
    
#     return {"name": doc.name, "plot_id": doc.plot_id}

# @frappe.whitelist()
# def update_land_plot(name, plot_data):
#     """Update an existing land plot"""
#     user = frappe.session.user
#     if user == "Guest":
#         frappe.throw(_("Not logged in"), frappe.PermissionError)

#     customer, supplier = _get_party_from_user(user)
#     if not supplier:
#         frappe.throw(_("Only Suppliers can update land plots"), frappe.PermissionError)

#     data = json.loads(plot_data) if isinstance(plot_data, str) else plot_data
    
#     doc = frappe.get_doc("Land Plot", name)
    
#     # Check ownership
#     if doc.supplier != supplier:
#         frappe.throw(_("Access denied"), frappe.PermissionError)
    
#     # Update fields
#     doc.plot_id = data.get("id") or data.get("plot_id", doc.plot_id)
#     doc.plot_name = data.get("name") or data.get("plot_name", doc.plot_name) 
#     doc.country = data.get("country", doc.country)
#     doc.area = data.get("area", doc.area)
#     doc.coordinates = json.dumps(data.get("coordinates", [])) if data.get("coordinates") else doc.coordinates
#     doc.geojson = json.dumps(data.get("geojson")) if data.get("geojson") else doc.geojson
#     doc.commodities = ",".join(data.get("commodities", [])) if data.get("commodities") else doc.commodities
    
#     # Update products - clear and re-add
#     doc.products = []
#     for product_id in data.get("products", []):
#         doc.append("products", {"product": product_id})
    
#     doc.save(ignore_permissions=True)
#     frappe.db.commit()
    
#     return {"success": True}

# @frappe.whitelist()
# def delete_land_plot(name):
#     """Delete a land plot"""
#     user = frappe.session.user
#     if user == "Guest":
#         frappe.throw(_("Not logged in"), frappe.PermissionError)

#     customer, supplier = _get_party_from_user(user)
#     if not supplier:
#         frappe.throw(_("Only Suppliers can delete land plots"), frappe.PermissionError)

#     doc = frappe.get_doc("Land Plot", name)
    
#     if doc.supplier != supplier:
#         frappe.throw(_("Access denied"), frappe.PermissionError)
    
#     frappe.delete_doc("Land Plot", name)
#     frappe.db.commit()
    
#     return {"success": True}

# @frappe.whitelist()
# def bulk_create_land_plots(plots_data):
#     """Create multiple land plots from CSV import"""
#     user = frappe.session.user
#     if user == "Guest":
#         frappe.throw(_("Not logged in"), frappe.PermissionError)

#     customer, supplier = _get_party_from_user(user)
#     if not supplier:
#         frappe.throw(_("Only Suppliers can create land plots"), frappe.PermissionError)

#     plots = json.loads(plots_data) if isinstance(plots_data, str) else plots_data
#     created_plots = []
    
#     for plot_data in plots:
#         try:
#             result = create_land_plot(plot_data)
#             created_plots.append(result)
#         except Exception as e:
#             frappe.log_error(f"Failed to create plot {plot_data.get('id', 'unknown')}: {str(e)}")
    
#     return {"created": len(created_plots), "plots": created_plots}

# # Keep the existing import functions for file handling
# @frappe.whitelist()
# def begin_import():
#     """Create a Land Plot Import doc (Draft) linked to logged-in supplier and return its name."""
#     user = frappe.session.user
#     if user == "Guest":
#         frappe.throw(_("Not logged in"), frappe.PermissionError)

#     customer, supplier = _get_party_from_user(user)
#     if not supplier:
#         frappe.throw(_("Only Suppliers can upload"), frappe.PermissionError)

#     doc = frappe.get_doc({
#         "doctype": "Land Plot Import",
#         "supplier": supplier,
#         "status": "Draft",
#     })
#     doc.insert(ignore_permissions=True)
#     frappe.db.commit()
#     return {"name": doc.name}

# @frappe.whitelist()
# def finalize_import(name: str, total_plots: int = 0, log: str | None = None, status: str | None = None):
#     """Mark an import as Imported (or Failed) and store counts/log."""
#     doc = frappe.get_doc("Land Plot Import", name)
#     doc.total_plots = int(total_plots or 0)
#     if status and status in {"Draft", "Imported", "Failed"}:
#         doc.status = status
#     else:
#         doc.status = "Imported"
#     if log is not None:
#         doc.log = log
#     doc.save(ignore_permissions=True)
#     frappe.db.commit()
#     return {"ok": True, "name": name, "file_url": doc.source_file}
import frappe
import json
import os
import ee
import uuid
from datetime import datetime
from frappe import _

# Earth Engine Configuration
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_KEY_PATH = os.path.join(CURRENT_DIR, "earthengine-key.json")
SERVICE_ACCOUNT = 'map-integration@igneous-nucleus-442113-m1.iam.gserviceaccount.com'

# Initialize Earth Engine
def init_earth_engine():
    """Initialize Earth Engine with service account credentials"""
    try:
        if not ee.data._credentials:
            credentials = ee.ServiceAccountCredentials(SERVICE_ACCOUNT, PRIVATE_KEY_PATH)
            ee.Initialize(credentials, project='igneous-nucleus-442113-m1')
    except Exception as e:
        safe_log_error(f"Earth Engine initialization failed: {str(e)}")
        print(f"Earth Engine init failed: {e}")

def safe_log_error(message, title=None, method="API"):
    """Safely log errors with proper length handling"""
    try:
        MAX_LENGTH = 135  # Leave some buffer for 140 char limit
        if title:
            truncated_title = (title[:MAX_LENGTH - 3] + '...') if len(title) > MAX_LENGTH else title
        else:
            truncated_title = (message[:MAX_LENGTH - 3] + '...') if len(message) > MAX_LENGTH else message
        
        # Use frappe's built-in logging
        frappe.log_error(message=message, title=truncated_title)
    except Exception as e:
        # If even logging fails, just print to console
        print(f"Logging failed: {str(e)}")
        print(f"Original error: {message}")

def generate_unique_plot_id(base_id=None, supplier=None):
    """Generate a unique plot ID"""
    if base_id:
        # Clean the base ID
        import re
        clean_id = re.sub(r'[^a-zA-Z0-9-_]', '', str(base_id).strip())
        if clean_id and len(clean_id) > 0:
            # Check if it already exists for this supplier
            existing = frappe.db.exists("Land Plot", {"plot_id": clean_id, "supplier": supplier})
            if not existing:
                return clean_id
            
            # If exists, try with suffix
            for i in range(1, 100):
                new_id = f"{clean_id}-{i:02d}"
                existing = frappe.db.exists("Land Plot", {"plot_id": new_id, "supplier": supplier})
                if not existing:
                    return new_id
    
    # Generate a unique timestamp-based ID
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique_suffix = str(uuid.uuid4())[:8].upper()
    return f"PLOT-{timestamp}-{unique_suffix}"

def calculate_deforestation_data(coordinates):
    """Calculate deforestation data for given coordinates"""
    try:
        init_earth_engine()
        
        if not coordinates or len(coordinates) == 0:
            return None
            
        # Handle single point coordinates (convert to small polygon)
        if len(coordinates) == 1:
            lng, lat = coordinates[0]
            # Create a small buffer around the point (about 100m radius)
            buffer_size = 0.001  # approximately 100m
            coords = [
                [lng - buffer_size, lat - buffer_size],
                [lng + buffer_size, lat - buffer_size],
                [lng + buffer_size, lat + buffer_size],
                [lng - buffer_size, lat + buffer_size],
                [lng - buffer_size, lat - buffer_size]
            ]
        else:
            coords = coordinates.copy()
            # Ensure polygon is closed
            if coords[0] != coords[-1]:
                coords.append(coords[0])

        polygon = ee.Geometry.Polygon([coords])

        # Load Hansen dataset
        gfc = ee.Image("UMD/hansen/global_forest_change_2024_v1_12")
        tree_cover_2000 = gfc.select("treecover2000")
        loss_year = gfc.select("lossyear")

        # Forest = tree cover ≥ 30%
        forest_mask = tree_cover_2000.gte(30)
        loss_after_2020 = loss_year.gt(20)

        # Area calculations
        pixel_area = ee.Image.pixelArea()
        forest_area_img = forest_mask.multiply(pixel_area)
        loss_area_img = loss_after_2020.multiply(forest_mask).multiply(pixel_area)

        forest_area = forest_area_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=polygon,
            scale=30,
            maxPixels=1e9
        ).get('treecover2000')

        loss_area = loss_area_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=polygon,
            scale=30,
            maxPixels=1e9
        ).get('lossyear')

        # Calculate statistics
        forest_area_ha = ee.Number(forest_area).divide(10000)
        loss_area_ha = ee.Number(loss_area).divide(10000)
        loss_percent = ee.Algorithms.If(
            forest_area_ha.gt(0),
            loss_area_ha.divide(forest_area_ha).multiply(100),
            0
        )

        stats = ee.Dictionary({
            "forest_area_ha": forest_area_ha,
            "loss_area_ha": loss_area_ha,
            "deforestation_percent": loss_percent
        }).getInfo()

        return {
            "forest_area_ha": round(stats["forest_area_ha"], 2),
            "loss_area_ha": round(stats["loss_area_ha"], 2),
            "deforestation_percent": round(stats["deforestation_percent"], 2)
        }

    except Exception as e:
        safe_log_error(f"Deforestation calculation failed: {str(e)}", "Deforestation Error")
        return None

        
@frappe.whitelist()
def get_deforestation_tiles(coordinates_json):
    """Generate Earth Engine tile URLs for deforestation visualization"""
    try:
        init_earth_engine()
        
        coordinates = json.loads(coordinates_json)
        if coordinates[0] != coordinates[-1]:
            coordinates.append(coordinates[0])

        polygon = ee.Geometry.Polygon([coordinates])

        # Load Hansen dataset
        gfc = ee.Image("UMD/hansen/global_forest_change_2024_v1_12")
        tree_cover_2000 = gfc.select("treecover2000")
        loss_year = gfc.select("lossyear")

        # Forest = tree cover ≥ 30%
        forest_mask = tree_cover_2000.gte(30)
        loss_after_2020 = loss_year.gt(20)

        # Create visualization parameters
        # Tree cover visualization (green shades)
        tree_cover_vis = {
            "min": 30, 
            "max": 100, 
            "palette": ["#d9f0a3", "#addd8e", "#78c679", "#41ab5d", "#238443", "#006837", "#004529"]
        }
        
        # Deforestation visualization (red)
        deforestation_vis = {
            "min": 1, 
            "max": 1, 
            "palette": ["red"]
        }
        
        # Loss year visualization (color by year)
        loss_year_vis = {
            "min": 21, 
            "max": 24, 
            "palette": ["yellow", "orange", "red", "darkred"]
        }

        # Generate tile URLs
        tree_cover_tile_info = tree_cover_2000.updateMask(forest_mask).getMapId(tree_cover_vis)
        deforestation_tile_info = loss_after_2020.selfMask().getMapId(deforestation_vis)
        loss_year_tile_info = loss_year.updateMask(loss_year.gt(20)).getMapId(loss_year_vis)

        # Calculate area statistics
        pixel_area = ee.Image.pixelArea()
        forest_area_img = forest_mask.multiply(pixel_area)
        loss_area_img = loss_after_2020.multiply(forest_mask).multiply(pixel_area)

        forest_area = forest_area_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=polygon,
            scale=30,
            maxPixels=1e9
        ).get('treecover2000')

        loss_area = loss_area_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=polygon,
            scale=30,
            maxPixels=1e9
        ).get('lossyear')

        # Calculate statistics
        forest_area_ha = ee.Number(forest_area).divide(10000)
        loss_area_ha = ee.Number(loss_area).divide(10000)
        loss_percent = ee.Algorithms.If(
            forest_area_ha.gt(0),
            loss_area_ha.divide(forest_area_ha).multiply(100),
            0
        )

        stats = ee.Dictionary({
            "forest_area_ha": forest_area_ha,
            "loss_area_ha": loss_area_ha,
            "deforestation_percent": loss_percent
        }).getInfo()

        return {
            "tree_cover_tile_url": tree_cover_tile_info['tile_fetcher'].url_format,
            "deforestation_tile_url": deforestation_tile_info['tile_fetcher'].url_format,
            "loss_year_tile_url": loss_year_tile_info['tile_fetcher'].url_format,
            "forest_area_ha": round(stats["forest_area_ha"], 2),
            "loss_area_ha": round(stats["loss_area_ha"], 2),
            "deforestation_percent": round(stats["deforestation_percent"], 2)
        }

    except Exception as e:
        safe_log_error(f"Error generating tile URLs: {str(e)}", "Tile Generation Error")
        frappe.throw(f"Error generating tile URLs: {str(e)}")

@frappe.whitelist()
def get_global_deforestation_tiles():
    """Generate global Earth Engine tile URLs for background deforestation layers"""
    try:
        init_earth_engine()

        # Load Hansen dataset
        gfc = ee.Image("UMD/hansen/global_forest_change_2024_v1_12")
        tree_cover_2000 = gfc.select("treecover2000")
        loss_year = gfc.select("lossyear")

        # Global layers
        forest_mask = tree_cover_2000.gte(30)
        loss_after_2020 = loss_year.gt(20)

        # Visualization parameters
        tree_cover_vis = {
            "min": 30, 
            "max": 100, 
            "palette": ["#d9f0a3", "#addd8e", "#78c679", "#41ab5d", "#238443", "#006837", "#004529"]
        }
        
        deforestation_vis = {
            "min": 1, 
            "max": 1, 
            "palette": ["#ff0000"]
        }

        # Generate global tile URLs
        global_tree_cover = tree_cover_2000.updateMask(forest_mask).getMapId(tree_cover_vis)
        global_deforestation = loss_after_2020.selfMask().getMapId(deforestation_vis)

        return {
            "global_tree_cover_url": global_tree_cover['tile_fetcher'].url_format,
            "global_deforestation_url": global_deforestation['tile_fetcher'].url_format
        }

    except Exception as e:
        safe_log_error(f"Error generating global tile URLs: {str(e)}", "Global Tile Error")
        frappe.throw(f"Error generating global tile URLs: {str(e)}")


# Helper function to get supplier from user
def _get_party_from_user(user):
    """Get supplier from user"""
    supplier_list = frappe.get_all("Supplier", 
        filters={"custom_user": user}, 
        fields=["name"]
    )
    if supplier_list:
        return None, supplier_list[0].name
    return None, None

@frappe.whitelist()
def get_land_plots():
    """Get all land plots for the logged-in supplier"""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    customer, supplier = _get_party_from_user(user)
    if not supplier:
        frappe.throw(_("Only Suppliers can access land plots"), frappe.PermissionError)

    plots = frappe.get_all("Land Plot", 
        filters={"supplier": supplier},
        fields=[
            "name", "plot_id", "plot_name", "country", "area", 
            "coordinates", "geojson", "latitude", "longitude",
            "commodities", "deforestation_percentage", "deforested_area",
            "deforested_polygons"
        ]
    )
    
    # Parse JSON fields and add products
    for plot in plots:
        try:
            if plot.coordinates:
                plot.coordinates = json.loads(plot.coordinates)
            if plot.geojson:
                plot.geojson = json.loads(plot.geojson)
            if plot.deforested_polygons:
                plot.deforested_polygons = json.loads(plot.deforested_polygons)
        except:
            pass
            
        # Get products
        products = frappe.get_all("Land Plot Product",
            filters={"parent": plot.name},
            fields=["product", "product_name"]
        )
        plot.products = [p.product for p in products]
        
        # Parse commodities 
        if plot.commodities:
            plot.commodities = [c.strip() for c in plot.commodities.split(',')]
        else:
            plot.commodities = []
    
    return {"data": plots}

def create_single_plot_internal(plot_data, supplier, calculate_deforestation=True):
    """Internal function to create a single plot with proper unique ID generation"""
    
    # Generate unique plot ID
    unique_plot_id = generate_unique_plot_id(plot_data.get('id'), supplier)
    
    # Double-check for duplicates (safety measure)
    counter = 1
    original_id = unique_plot_id
    while frappe.db.exists("Land Plot", {"plot_id": unique_plot_id, "supplier": supplier}):
        unique_plot_id = f"{original_id}-{counter:03d}"
        counter += 1
        if counter > 999:  # Safety limit
            unique_plot_id = f"PLOT-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            break
    
    # Calculate deforestation data if coordinates are provided
    deforestation_data = None
    if calculate_deforestation and plot_data.get('coordinates'):
        coordinates = plot_data.get('coordinates')
        if isinstance(coordinates, str):
            try:
                coordinates = json.loads(coordinates)
            except:
                coordinates = None
        
        if coordinates:
            print(f"Calculating deforestation for plot {unique_plot_id}...")
            try:
                deforestation_data = calculate_deforestation_data(coordinates)
                if deforestation_data:
                    print(f"Deforestation calculation complete: {deforestation_data['deforestation_percent']}%")
            except Exception as e:
                print(f"Deforestation calculation failed: {str(e)}")
                safe_log_error(f"Deforestation calc failed for {unique_plot_id}: {str(e)}", "Deforestation Error")
                deforestation_data = None
    
    # Create the main document
    doc = frappe.get_doc({
        "doctype": "Land Plot",
        "plot_id": unique_plot_id,  # Use the generated unique ID
        "plot_name": plot_data.get("name", "Unnamed Plot"),
        "supplier": supplier,
        "country": plot_data.get("country", ""),
        "area": float(plot_data.get("area", 0)),
        "latitude": float(plot_data.get("latitude")) if plot_data.get("latitude") else None,
        "longitude": float(plot_data.get("longitude")) if plot_data.get("longitude") else None,
        "coordinates": json.dumps(plot_data.get("coordinates", [])) if plot_data.get("coordinates") else None,
        "geojson": json.dumps(plot_data.get("geojson")) if plot_data.get("geojson") else None,
        "commodities": ",".join(plot_data.get("commodities", [])),
        # Set deforestation data from calculation
        "deforestation_percentage": deforestation_data["deforestation_percent"] if deforestation_data else 0,
        "deforested_area": deforestation_data["loss_area_ha"] if deforestation_data else 0,
        "deforested_polygons": None  # Can be enhanced later
    })
    
    # Add products
    for product_id in plot_data.get("products", []):
        if product_id:
            doc.append("products", {
                "product": product_id
            })
    
    doc.insert(ignore_permissions=True)
    return {"name": doc.name, "plot_id": doc.plot_id, "deforestation_data": deforestation_data}

@frappe.whitelist()
def create_land_plot(plot_data, calculate_deforestation=True):
    """Create a new land plot with deforestation calculation"""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    customer, supplier = _get_party_from_user(user)
    if not supplier:
        frappe.throw(_("Only Suppliers can create land plots"), frappe.PermissionError)

    data = json.loads(plot_data) if isinstance(plot_data, str) else plot_data
    result = create_single_plot_internal(data, supplier, calculate_deforestation)
    frappe.db.commit()
    return result

@frappe.whitelist()
def update_land_plot(name, plot_data, recalculate_deforestation=False):
    """Update an existing land plot with optional deforestation recalculation"""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    customer, supplier = _get_party_from_user(user)
    if not supplier:
        frappe.throw(_("Only Suppliers can update land plots"), frappe.PermissionError)

    data = json.loads(plot_data) if isinstance(plot_data, str) else plot_data
    
    doc = frappe.get_doc("Land Plot", name)
    
    # Check ownership
    if doc.supplier != supplier:
        frappe.throw(_("Access denied"), frappe.PermissionError)
    
    # Update fields
    doc.plot_id = data.get("id") or data.get("plot_id", doc.plot_id)
    doc.plot_name = data.get("name") or data.get("plot_name", doc.plot_name) 
    doc.country = data.get("country", doc.country)
    doc.area = data.get("area", doc.area)
    doc.coordinates = json.dumps(data.get("coordinates", [])) if data.get("coordinates") else doc.coordinates
    doc.geojson = json.dumps(data.get("geojson")) if data.get("geojson") else doc.geojson
    doc.commodities = ",".join(data.get("commodities", [])) if data.get("commodities") else doc.commodities
    
    # Recalculate deforestation if requested and coordinates changed
    if recalculate_deforestation and data.get('coordinates'):
        coordinates = data.get('coordinates')
        if isinstance(coordinates, str):
            try:
                coordinates = json.loads(coordinates)
            except:
                coordinates = None
        
        if coordinates:
            print(f"Recalculating deforestation for plot {doc.plot_id}...")
            deforestation_data = calculate_deforestation_data(coordinates)
            if deforestation_data:
                doc.deforestation_percentage = deforestation_data["deforestation_percent"]
                doc.deforested_area = deforestation_data["loss_area_ha"]
                print(f"Deforestation recalculation complete: {deforestation_data['deforestation_percent']}%")
    
    # Update products - clear and re-add
    doc.products = []
    for product_id in data.get("products", []):
        doc.append("products", {"product": product_id})
    
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {"success": True}

@frappe.whitelist()
def bulk_create_land_plots(plots_data, calculate_deforestation=True):
    """Create multiple land plots with proper error handling and unique IDs"""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    customer, supplier = _get_party_from_user(user)
    if not supplier:
        frappe.throw(_("Only Suppliers can create land plots"), frappe.PermissionError)

    plots = json.loads(plots_data) if isinstance(plots_data, str) else plots_data
    created_plots = []
    failed_plots = []
    
    # Initialize Earth Engine once for all plots
    if calculate_deforestation:
        init_earth_engine()
    
    for i, plot_data in enumerate(plots):
        try:
            # Create plot with unique ID generation
            result = create_single_plot_internal(plot_data, supplier, calculate_deforestation)
            created_plots.append(result)
            frappe.db.commit()  # Commit each successful creation
            
        except Exception as e:
            error_msg = f"Plot {plot_data.get('id', f'Plot_{i+1}')}: {str(e)}"
            failed_plots.append({
                'plot_id': plot_data.get('id', f'Plot_{i+1}'),
                'error': str(e)
            })
            
            # Use safe logging to avoid character length issues
            safe_log_error(error_msg, f"Plot Creation Failed", "bulk_create")
            frappe.db.rollback()  # Rollback this individual failure
            
            print(f"Failed to create plot {plot_data.get('id', f'Plot_{i+1}')}: {str(e)}")
    
    # Final commit for all successful creations
    frappe.db.commit()
    
    return {
        "created": len(created_plots), 
        "failed": len(failed_plots),
        "created_plots": created_plots,
        "failed_plots": failed_plots
    }

@frappe.whitelist()
def recalculate_deforestation(plot_name):
    """Manually recalculate deforestation for a specific plot"""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    customer, supplier = _get_party_from_user(user)
    if not supplier:
        frappe.throw(_("Only Suppliers can update land plots"), frappe.PermissionError)

    doc = frappe.get_doc("Land Plot", plot_name)
    
    # Check ownership
    if doc.supplier != supplier:
        frappe.throw(_("Access denied"), frappe.PermissionError)
    
    if not doc.coordinates:
        frappe.throw(_("No coordinates available for deforestation calculation"))
    
    try:
        coordinates = json.loads(doc.coordinates)
        deforestation_data = calculate_deforestation_data(coordinates)
        
        if deforestation_data:
            doc.deforestation_percentage = deforestation_data["deforestation_percent"]
            doc.deforested_area = deforestation_data["loss_area_ha"]
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            return {
                "success": True,
                "deforestation_data": deforestation_data
            }
        else:
            frappe.throw(_("Failed to calculate deforestation data"))
            
    except Exception as e:
        safe_log_error(f"Failed to recalculate deforestation for {plot_name}: {str(e)}", "Deforestation Recalc Error")
        frappe.throw(_("Error calculating deforestation: {0}").format(str(e)))

@frappe.whitelist()
def delete_land_plot(name):
    """Delete a land plot"""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    customer, supplier = _get_party_from_user(user)
    if not supplier:
        frappe.throw(_("Only Suppliers can delete land plots"), frappe.PermissionError)

    doc = frappe.get_doc("Land Plot", name)
    
    if doc.supplier != supplier:
        frappe.throw(_("Access denied"), frappe.PermissionError)
    
    frappe.delete_doc("Land Plot", name)
    frappe.db.commit()
    
    return {"success": True}

# Keep your existing functions for file import
@frappe.whitelist()
def begin_import():
    """Create a Land Plot Import doc"""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    customer, supplier = _get_party_from_user(user)
    if not supplier:
        frappe.throw(_("Only Suppliers can upload"), frappe.PermissionError)

    doc = frappe.get_doc({
        "doctype": "Land Plot Import",
        "supplier": supplier,
        "status": "Draft",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name}

@frappe.whitelist()
def finalize_import(name: str, total_plots: int = 0, log: str = None, status: str = None):
    """Mark an import as completed"""
    doc = frappe.get_doc("Land Plot Import", name)
    doc.total_plots = int(total_plots or 0)
    if status and status in {"Draft", "Imported", "Failed"}:
        doc.status = status
    else:
        doc.status = "Imported"
    if log is not None:
        doc.log = log
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "name": name, "file_url": doc.source_file}
