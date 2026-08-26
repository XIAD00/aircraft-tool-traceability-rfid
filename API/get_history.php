<?php

// Get the checkout and return history of one tool.
require_once "connect.php";

header("Content-Type: application/json; charset=utf-8");
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

function history_response($status, $payload)
{
    http_response_code($status);
    echo json_encode($payload);
    exit();
}

if ($_SERVER["REQUEST_METHOD"] !== "GET") {
    header("Allow: GET");
    history_response(405, ["success" => false, "message" => "Méthode non autorisée."]);
}

$uid = isset($_GET["rfid_uid"]) ? strtoupper(trim($_GET["rfid_uid"])) : "";

if ($uid === "" || strlen($uid) > 50) {
    history_response(400, ["success" => false, "message" => "UID invalide."]);
}

try {
    $sql = "
        SELECT
            tr.transaction_id,
            tr.rfid_uid,
            tr.borrow_date AS scan_time,
            'CHECK_OUT' AS actions,
            tr.matricule,
            emp.first_name,
            emp.last_name,
            emp.department,
            emp.service
        FROM transactions tr
        LEFT JOIN employees emp ON emp.matricule = tr.matricule
        WHERE tr.rfid_uid = ? AND tr.borrow_date IS NOT NULL

        UNION ALL

        SELECT
            tr.transaction_id,
            tr.rfid_uid,
            tr.return_date AS scan_time,
            'CHECK_IN' AS actions,
            tr.matricule,
            emp.first_name,
            emp.last_name,
            emp.department,
            emp.service
        FROM transactions tr
        LEFT JOIN employees emp ON emp.matricule = tr.matricule
        WHERE tr.rfid_uid = ? AND tr.return_date IS NOT NULL

        ORDER BY scan_time DESC, transaction_id DESC
    ";

    $stmt = $conn->prepare($sql);
    $stmt->bind_param("ss", $uid, $uid);
    $stmt->execute();
    $result = $stmt->get_result();

    $history = [];
    while ($row = $result->fetch_assoc()) {
        unset($row["transaction_id"]);
        $history[] = $row;
    }

    $stmt->close();
    history_response(200, ["success" => true, "data" => $history]);
} catch (Throwable $error) {
    history_response(500, [
        "success" => false,
        "message" => "Impossible de récupérer l'historique."
    ]);
}
