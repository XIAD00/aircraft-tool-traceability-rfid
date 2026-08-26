<?php

// Delete one tool from the database.
require_once "connect.php";

header("Content-Type: application/json; charset=utf-8");
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

function delete_response($status, $payload)
{
    http_response_code($status);
    echo json_encode($payload);
    exit();
}

if ($_SERVER["REQUEST_METHOD"] !== "POST") {
    header("Allow: POST");
    delete_response(405, ["success" => false, "message" => "Méthode non autorisée."]);
}

$data = json_decode(file_get_contents("php://input"), true);
$uid = is_array($data)
    ? strtoupper(trim((string) ($data["rfid_uid"] ?? "")))
    : "";

if ($uid === "" || strlen($uid) > 50) {
    delete_response(400, ["success" => false, "message" => "UID invalide."]);
}

try {
    $stmt = $conn->prepare("DELETE FROM tools WHERE rfid_uid = ?");
    $stmt->bind_param("s", $uid);
    $stmt->execute();
    $deleted = $stmt->affected_rows;
    $stmt->close();

    if ($deleted !== 1) {
        delete_response(404, ["success" => false, "message" => "Outil introuvable."]);
    }

    delete_response(200, [
        "success" => true,
        "message" => "Outil supprimé."
    ]);
} catch (mysqli_sql_exception $error) {
    if ((int) $error->getCode() === 1451) {
        delete_response(409, [
            "success" => false,
            "message" => "Cet outil possède un historique et ne peut pas être supprimé."
        ]);
    }

    delete_response(500, [
        "success" => false,
        "message" => "Impossible de supprimer l'outil."
    ]);
}
