<?php

// Get the latest RFID scans for the desktop app.
require_once "connect.php";

header("Content-Type: application/json; charset=utf-8");
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

try {
    $result = $conn->query("
        SELECT
            logs.scan_time,
            logs.rfid_uid,
            logs.actions,
            tools.part_number,
            tools.serial_number,
            tools.description_tool,
            tools.status_
        FROM rfid_logs logs
        LEFT JOIN tools ON tools.rfid_uid = logs.rfid_uid
        ORDER BY logs.log_id DESC
    ");

    $logs = [];
    while ($row = $result->fetch_assoc()) {
        $logs[] = $row;
    }

    echo json_encode($logs);
} catch (Throwable $error) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Impossible de récupérer les scans."
    ]);
}

$conn->close();
