<?php

// Get the last RFID scan and suggest the next action.
require_once "connect.php";

header("Content-Type: application/json; charset=utf-8");
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

try {
    $sql = "
        SELECT
            logs.log_id,
            logs.rfid_uid,
            logs.actions,
            logs.scan_time,
            tools.description_tool,
            tools.part_number,
            tools.serial_number,
            tools.status_,
            CASE
                WHEN tools.status_ = 'AVAILABLE' THEN 'CHECK_OUT'
                WHEN tools.status_ = 'BORROWED' THEN 'CHECK_IN'
                ELSE NULL
            END AS suggested_action
        FROM rfid_logs logs
        JOIN tools ON tools.rfid_uid = logs.rfid_uid
        ORDER BY logs.log_id DESC
        LIMIT 1
    ";

    $result = $conn->query($sql);

    if ($result->num_rows > 0) {
        $scan = $result->fetch_assoc();
        $scan["log_id"] = (int) $scan["log_id"];
        echo json_encode($scan);
    } else {
        echo json_encode(null);
    }
} catch (Throwable $error) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Impossible de récupérer le dernier scan."
    ]);
}

$conn->close();
