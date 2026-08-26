<?php

// Save a scanned UID and return the tool information.
require_once "connect.php";

header("Content-Type: application/json; charset=utf-8");
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

function respond($status, $payload)
{
    http_response_code($status);
    echo json_encode($payload);
    exit();
}

if ($_SERVER["REQUEST_METHOD"] !== "GET") {
    header("Allow: GET");
    respond(405, ["success" => false, "message" => "Méthode non autorisée."]);
}

$uid = isset($_GET["uid"]) ? strtoupper(trim($_GET["uid"])) : "";

if ($uid === "" || strlen($uid) > 50) {
    respond(400, ["success" => false, "message" => "UID invalide."]);
}

try {
    $stmt = $conn->prepare("
        SELECT rfid_uid, part_number, serial_number, description_tool,
               last_check, next_check, status_
        FROM tools
        WHERE rfid_uid = ?
    ");
    $stmt->bind_param("s", $uid);
    $stmt->execute();
    $tool = $stmt->get_result()->fetch_assoc();
    $stmt->close();

    if (!$tool) {
        respond(404, ["success" => false, "message" => "Outil inconnu."]);
    }

    $action = "SCAN";
    $log = $conn->prepare("
        INSERT INTO rfid_logs (rfid_uid, actions)
        VALUES (?, ?)
    ");
    $log->bind_param("ss", $uid, $action);
    $log->execute();
    $logId = $conn->insert_id;
    $log->close();

    $status = strtoupper($tool["status_"]);
    $suggestedAction = null;

    if ($status === "AVAILABLE") {
        $suggestedAction = "CHECK_OUT";
    } elseif ($status === "BORROWED") {
        $suggestedAction = "CHECK_IN";
    }

    respond(200, [
        "success" => true,
        "log_id" => (int) $logId,
        "action" => "SCAN",
        "suggested_action" => $suggestedAction,
        "tool" => $tool
    ]);
} catch (Throwable $error) {
    respond(500, [
        "success" => false,
        "message" => "Impossible d'enregistrer le scan."
    ]);
}
