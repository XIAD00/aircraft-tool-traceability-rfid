# Send requests from the desktop app to the PHP API.

import requests

from config import API_URL


REQUEST_TIMEOUT = 5


def _error_result(message, status_code=None):
    result = {
        "success": False,
        "message": message
    }
    if status_code is not None:
        result["status_code"] = status_code
    return result


def _request_json(method, endpoint, **kwargs):
    try:
        response = requests.request(
            method,
            f"{API_URL}/{endpoint}",
            timeout=REQUEST_TIMEOUT,
            **kwargs
        )
    except requests.Timeout:
        return None, _error_result("Le serveur ne répond pas dans le délai prévu.")
    except requests.RequestException:
        return None, _error_result("Le serveur RFID est indisponible.")

    try:
        data = response.json()
    except ValueError:
        return None, _error_result(
            "La réponse du serveur est invalide.",
            response.status_code
        )

    if not response.ok:
        if response.status_code >= 500:
            message = "Erreur interne du serveur."
        elif isinstance(data, dict):
            message = data.get("message", "La demande a été refusée.")
        else:
            message = "La demande a été refusée."

        return None, _error_result(message, response.status_code)

    return data, None


def get_tools():
    data, error = _request_json("GET", "get_tools.php")
    if error or not isinstance(data, list):
        return []
    return data


def add_tool(data):
    response, error = _request_json("POST", "add_tool.php", json=data)
    if error:
        return error
    if not isinstance(response, dict):
        return _error_result("La réponse du serveur est invalide.")
    return response


def update_tool(data):
    response, error = _request_json("POST", "update_tool.php", json=data)
    if error:
        return error
    if not isinstance(response, dict):
        return _error_result("La réponse du serveur est invalide.")
    return response


def delete_tool(rfid_uid):
    response, error = _request_json(
        "POST",
        "delete_tool.php",
        json={"rfid_uid": rfid_uid}
    )
    if error:
        return error
    if not isinstance(response, dict):
        return _error_result("La réponse du serveur est invalide.")
    return response


def scan_tool(uid):
    response, error = _request_json(
        "GET",
        "scan_tool.php",
        params={"uid": uid}
    )
    if error:
        return error
    if not isinstance(response, dict):
        return _error_result("La réponse du serveur est invalide.")
    return response


def get_last_scan():
    response, error = _request_json("GET", "last_scan.php")
    if error:
        return None
    if response is None or isinstance(response, dict):
        return response
    return None


def get_logs():
    data, error = _request_json("GET", "get_logs.php")
    if error or not isinstance(data, list):
        return []
    return data


def get_history(rfid_uid):
    response, error = _request_json(
        "GET",
        "get_history.php",
        params={"rfid_uid": rfid_uid}
    )
    if error or not isinstance(response, dict):
        return []
    if response.get("success"):
        history = response.get("data", [])
        return history if isinstance(history, list) else []
    return []


def get_employee(matricule):
    response, error = _request_json(
        "GET",
        "get_employee.php",
        params={"matricule": matricule}
    )
    if error:
        return error
    if not isinstance(response, dict):
        return _error_result("La réponse du serveur est invalide.")
    return response


def confirm_transaction(log_id, uid, matricule, action):
    response, error = _request_json(
        "POST",
        "confirm_transaction.php",
        json={
            "log_id": log_id,
            "rfid_uid": uid,
            "matricule": matricule,
            "action": action
        }
    )
    if error:
        return error
    if not isinstance(response, dict):
        return _error_result("La réponse du serveur est invalide.")
    return response
