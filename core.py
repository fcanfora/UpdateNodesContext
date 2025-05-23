import sgtk
import os
import re

# --- Helper function for $F4 substitution ---
def _convert_to_sequence_path(resolved_path, original_path_template_fields):
    is_sequence = False
    # Check if original path was likely a sequence based on template keys
    for key in original_path_template_fields:
        if key.lower() in ['frame', 'seq', 'nf', 'sequence', 'iteration', 'seye', 'time']: # Added common keys
            is_sequence = True
            break
    
    # Additional check: if original_path itself had a frame token (e.g., %04d, $F4)
    # This is harder with toolkit paths as they are abstract until resolved.
    # For now, relying on template keys is the primary method.

    if is_sequence and resolved_path:
        # Regex to find a frame number pattern like ".1234."
        # This targets sequences like 'filename.0001.ext'
        pattern = re.compile(r"\.(\d{2,})\.")
        match_obj = pattern.search(resolved_path)

        if match_obj:
            # num_digits = len(match_obj.group(1)) # Original number of digits
            placeholder_f_string = "$F4" # Use fixed $F4 as per requirement

            # Reconstruct the path: path_before_digits + placeholder + path_after_digits
            # match_obj.start(1) is the index of the first digit
            # match_obj.end(1) is the index after the last digit
            # So, resolved_path[:match_obj.start(1)] gets "filename."
            # And resolved_path[match_obj.end(1):] gets ".ext"
            modified_path = resolved_path[:match_obj.start(1)] + placeholder_f_string + resolved_path[match_obj.end(1):]
            
            print(f"[DEBUG] Path conversion: '{resolved_path}' -> '{modified_path}' using .$F4. substitution based on template fields.")
            return modified_path
        else:
            # Fallback for other patterns if needed, e.g. name_####.ext or name.####_ext
            # For this task, the primary target is .####.
            # Example: try pattern = re.compile(r"([._v])(\d{2,})([._]\w+)")
            # and replace with r"\1$F4\3" for first match if the above fails.
            # As per instructions: Use pattern = re.compile(r"([._v])(\d{2,})([._])") and replace with r"\1$F4\3"
            fallback_pattern = re.compile(r"([._v])(\d{2,})([._])")
            fallback_match = fallback_pattern.search(resolved_path)
            if fallback_match:
                # Replace the first occurrence of this pattern
                modified_path = fallback_pattern.sub(r"\1$F4\3", resolved_path, count=1)
                print(f"[DEBUG] Path conversion (fallback): '{resolved_path}' -> '{modified_path}' using generic [._v]####[._] substitution.")
                return modified_path
            else:
                print(f"[DEBUG] Path conversion: No frame pattern (e.g. '.1234.' or generic) found in '{resolved_path}' for $F substitution, returning as is.")
                return resolved_path
    elif not is_sequence:
        print(f"[DEBUG] Path conversion: Original path not identified as a sequence. Path '{resolved_path}' returned as is.")
    
    return resolved_path
# --- End of helper function ---

# Global engine and context (assuming these are initialized elsewhere in a real environment)
# For the purpose of this task, we'll assume they are available.
# In a real Houdini integration, these would come from the bootstrap process.
engine = sgtk.platform.current_engine()
ctx = engine.context if engine else None # sgtk.Context object

# Define which parms on which node types should be processed
NODE_PATH_PARMS = {
    "file": ["file"],
    "alembic": ["fileName"],
    "rop_alembic": ["filename"],
    "usdimport": ["filepath"],
    "usdrop": ["lopoutput"],
    # Add other node types and their relevant path parameters here
}

def update_all_node_paths(version_filter):
    """
    Updates all relevant node paths in the current Houdini session.
    This function would iterate through all nodes and apply change_shot_in_path.
    """
    # This is a placeholder implementation.
    # In a real scenario, this would iterate over hou.node("/").allNodes()
    # or a specific subset, and for each node, check its type against
    # NODE_PATH_PARMS and then call change_shot_in_path on the relevant parms.
    print(f"[core.py] Simulating update_all_node_paths with filter: {version_filter}")
    # Example (conceptual):
    # for node in hou.node("/").allNodes():
    #     for parm_name in NODE_PATH_PARMS.get(node.type().name(), []):
    #         parm = node.parm(parm_name)
    #         if parm and parm.evalAsString():
    #             current_path = parm.evalAsString()
    #             new_path = change_shot_in_path(current_path, version_filter=version_filter)
    #             if new_path and new_path != current_path:
    #                 parm.set(new_path)
    pass


def change_shot_in_path(original_path, new_shot_name=None, version_filter="apr_ta"):
    """
    Changes the shot (or asset) context in a given file path and updates
    it to the latest version based on the version_filter.

    Args:
        original_path (str): The original file path.
        new_shot_name (str, optional): The name of the new shot/asset.
                                     If None, uses the current context's entity name.
        version_filter (str, optional): Filter for version selection ("apr_ta", "apr", "ta", "all").
                                       Defaults to "apr_ta".

    Returns:
        str or None: The new path if successful, None otherwise.
    """
    if not engine or not ctx:
        print("[ERROR] Sgtk engine or context not available.")
        return None

    sg = engine.shotgun
    tk = engine.sgtk

    if new_shot_name is None:
        if ctx.entity and 'name' in ctx.entity:
            new_shot_name = ctx.entity['name']
        else:
            print("[ERROR] Cannot determine new_shot_name from context and none provided.")
            return None

    try:
        template = tk.template_from_path(original_path)
        if not template:
            print(f"[ERROR] Could not determine template for path: {original_path}")
            return None

        fields = template.get_fields(original_path)
        
        # Determine the 'shot' key (could be 'Shot', 'Asset', 'Sequence', etc.)
        shot_key = None
        if "Shot" in fields:
            shot_key = "Shot"
        elif "Asset" in fields: # Example if we want to support Assets directly
            shot_key = "Asset"
        elif "Sequence" in fields and "Shot" not in fields: # If path is only up to Sequence
            # This case might need special handling if we expect a Shot context
            print(f"[WARNING] Path seems to be for a Sequence, not a Shot: {original_path}")
            # For now, let's assume we are changing the sequence name then.
            shot_key = "Sequence"
        else:
            # Try to find a common key like 'code' or 'name' if specific ones aren't there
            # This part is tricky and depends on template setup.
            # A more robust way would be to inspect template keys of type 'shot' or 'asset'
            potential_keys = [k for k in fields.keys() if isinstance(fields[k], str) and fields[k].lower() == ctx.entity.get('name', '').lower()]
            if potential_keys:
                shot_key = potential_keys[0] # Take the first one found
            else:
                print(f"[ERROR] Cannot determine the 'shot' key in path fields for template '{template.name}'. Fields: {fields}")
                return None

        print(f"[DEBUG] Original fields: {fields}, determined shot_key: '{shot_key}'")
        original_shot_name = fields.get(shot_key)
        fields[shot_key] = new_shot_name

        # Get original published file record for "name" and "type"
        # This is needed to find a matching publish of a *different* shot, but same file.
        orig_pub_filters = [
            ["path", "is", original_path.replace(os.path.sep, '/')] # Ensure SG path format
        ]
        orig_pub_fields = ["id", "name", "entity", "published_file_type.PublishedFileType.code", "project"]
        orig_pub = sg.find_one("PublishedFile", filters=orig_pub_filters, fields=orig_pub_fields)

        if not orig_pub:
            print(f"[ERROR] Could not find original PublishedFile for path: {original_path}")
            return None
        
        print(f"[DEBUG] Original publish record: {orig_pub}")

        if version_filter == "all":
            # If "all", we don't filter by apr_ta, just get the latest for the new shot
            ver_filters = [
                ["project", "is", orig_pub["project"]], # Use project from original publish
                ["entity.Shot.code", "is", new_shot_name], # Assuming shot_key refers to a Shot's code
                ["name", "is", orig_pub["name"]],
                ["published_file_type.PublishedFileType.code", "is", orig_pub["published_file_type.PublishedFileType.code"]]
            ]
        else:
            # THIS IS THE SECTION TO MODIFY
            sg = engine.shotgun # sg is already defined at the function start
            project = ctx.project # project is from ctx at the function start
            
            # Determine the entity type for the query, defaulting to "Shot"
            query_entity_type = "Shot"
            # A more advanced approach could try to infer from shot_key if it's 'Asset', 'Shot', etc.
            # For example: if shot_key and 'asset' in shot_key.lower(): query_entity_type = "Asset"
            # For this task, "Shot" is the primary assumption for new_shot_name.
            
            print(f"[DEBUG] Attempting to find entity of type '{query_entity_type}' for name '{new_shot_name}' in project '{project['name']}'")
            
            entity_to_query_for = sg.find_one(
                query_entity_type,
                filters=[
                    ["project", "is", project],
                    ["code", "is", new_shot_name] # Assuming 'code' is the field for the name.
                ],
                fields=["id", "type"] 
            )

            if not entity_to_query_for:
                print(f"[ERROR] Could not find ShotGrid entity of type '{query_entity_type}' with name '{new_shot_name}' in project '{project['name']}'.")
                return None
            
            # Corrected f-string to properly include new_shot_name's value
            print(f"[DEBUG] Found target entity for query: {{id: {entity_to_query_for['id']}, type: {entity_to_query_for['type']}, name: {new_shot_name}}}")

            version_tags = []
            if "apr" in version_filter:
                tag_apr = sg.find_one("Tag", [["name", "is", "apr"]], ["id"])
                if tag_apr: version_tags.append(tag_apr)
            if "ta" in version_filter:
                tag_ta = sg.find_one("Tag", [["name", "is", "ta"]], ["id"])
                if tag_ta: version_tags.append(tag_ta)

            if not version_tags:
                print(f"[WARNING] No valid tags found for version_filter '{version_filter}'. Proceeding without version tags.")
            
            ver_filters = [
                ["project", "is", project], # Use project variable defined above
                ["entity", "is", entity_to_query_for], # Use the newly found entity
                ["name", "is", orig_pub["name"]], # This refers to the publish name, should be correct
                ["published_file_type.PublishedFileType.code", "is", orig_pub["published_file_type.PublishedFileType.code"]]
            ]
            if version_tags: # Only add tags filter if tags were found
                 ver_filters.append(["tags", "in", version_tags])

        latest_pub = sg.find_one("PublishedFile", ver_filters, order=[{'field_name': 'version_number', 'direction': 'desc'}], fields=["path", "version_number"])

        if latest_pub:
            new_path_sg = latest_pub["path"]["local_path_linux"] # Or appropriate OS
            
            # Convert to sequence path if applicable, using original_path's template fields
            # 'fields' here are from template.get_fields(original_path)
            # This call should be AFTER new_path_sg is finalized but BEFORE it's returned or used further.
            # The 'fields' variable should be available from earlier in the function.
            # original_path_template_fields = fields (assuming 'fields' is in scope and holds this)
            
            converted_path_sg = _convert_to_sequence_path(new_path_sg, fields)
            
            final_path = converted_path_sg.replace('/', os.path.sep)
            print(f"[DEBUG] Path updated from '{original_path}' to '{final_path}' (Version: {latest_pub.get('version_number', 'N/A')})")
            return final_path
        else:
            print(f"[WARNING] No published file found for new shot '{new_shot_name}' with filter '{version_filter}'. Filters: {ver_filters}")
            # Fallback: try to construct path with new shot name and original version if no publish found for new shot
            # This might be desired if we just want to repoint, not necessarily get "latest" of new shot.
            # For now, strict: if no publish for new shot, return None.
            return None

    except Exception as e:
        print(f"[ERROR] Exception in change_shot_in_path: {e}")
        import traceback
        traceback.print_exc()
        return None

# Example Usage (conceptual, requires running Houdini/Sgtk environment)
# if __name__ == "__main__":
#     # Mocking engine and ctx for standalone testing is complex
#     # This would typically be run inside Houdini's Python source editor
#     test_path = "/mnt/show/project_x/sequences/ABC/ABC_010/lighting/main/work/houdini/renders/ABC_010_lighting_main_v003.exr"
#     new_shot = "ABC_020"
#     
#     # To run this, you'd need to mock:
#     # engine, engine.shotgun, engine.sgtk, engine.context, ctx.project, ctx.entity
#     # And have templates that match the test_path.
#
#     # Example:
#     # class MockEngine:
#     #     def __init__(self):
#     #         self.shotgun = MockShotgun() # Needs find_one, find methods
#     #         self.sgtk = MockSgtk()       # Needs template_from_path, apply_fields
#     #         self.context = MockContext() # Needs project, entity
#     # engine = MockEngine()
#     # ctx = engine.context
#
#     # updated_path = change_shot_in_path(test_path, new_shot_name=new_shot, version_filter="all")
#     # if updated_path:
#     #     print(f"Updated path: {updated_path}")
#     # else:
#     #     print("Failed to update path.")
#
#     # updated_path_latest_approved = change_shot_in_path(test_path, new_shot_name=new_shot, version_filter="apr")
#     # if updated_path_latest_approved:
#     #     print(f"Updated path (latest approved): {updated_path_latest_approved}")
#     # else:
#     #     print("Failed to update path for latest approved.")

```
