# Connect the interface actions with the API functions.

from api import (
    get_tools,
    add_tool,
    update_tool,
    delete_tool,
    scan_tool,
    get_last_scan,
    get_logs,
    get_history,
    get_employee,
    confirm_transaction
)

class ToolManager:

    def get_all_tools(self):
        return get_tools()

    def add_tool(self, data):
        return add_tool(data)

    def get_last_scan(self):
        return get_last_scan()

    def get_logs(self):
        return get_logs()

    def update_tool(self, data):
        return update_tool(data)

    def delete_tool(self, rfid_uid):
        return delete_tool(rfid_uid)

    def scan_tool(self, uid):
        return scan_tool(uid)

    def get_tool_history(self, rfid_uid):
        return get_history(rfid_uid)

    def verify_employee(self, matricule):
        return get_employee(matricule)

    def confirm_transaction(self, log_id, uid, matricule, action):
        return confirm_transaction(log_id, uid, matricule, action)
