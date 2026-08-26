<?php

// Confirm a tool checkout or return after an RFID scan.
require_once "connect.php";

header("Content-Type: application/json; charset=utf-8");
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);

class ApiTransactionException extends RuntimeException
{
    public $status;

    public function __construct($status, $message)
    {
        parent::__construct($message);
        $this->status = $status;
    }
}

function transaction_response($status, $payload)
{
    http_response_code($status);
    echo json_encode($payload);
    exit();
}

function transaction_fail($status, $message)
{
    throw new ApiTransactionException($status, $message);
}

if ($_SERVER["REQUEST_METHOD"] !== "POST") {
    header("Allow: POST");
    transaction_response(405, ["success" => false, "message" => "Méthode non autorisée."]);
}

$data = json_decode(file_get_contents("php://input"), true);

if (!is_array($data)) {
    transaction_response(400, ["success" => false, "message" => "Corps JSON invalide."]);
}

$logId = filter_var($data["log_id"] ?? null, FILTER_VALIDATE_INT, [
    "options" => ["min_range" => 1]
]);
$uid = strtoupper(trim((string) ($data["rfid_uid"] ?? "")));
$matricule = strtoupper(trim((string) ($data["matricule"] ?? "")));
$action = strtoupper(trim((string) ($data["action"] ?? "")));

if ($logId === false || $uid === "" || strlen($uid) > 50) {
    transaction_response(400, ["success" => false, "message" => "Données de scan invalides."]);
}

if (
    $matricule === "" ||
    strlen($matricule) > 20 ||
    !preg_match('/^[A-Z0-9._-]+$/', $matricule)
) {
    transaction_response(400, ["success" => false, "message" => "Matricule invalide."]);
}

if (!in_array($action, ["CHECK_OUT", "CHECK_IN"], true)) {
    transaction_response(400, ["success" => false, "message" => "Action invalide."]);
}

$transactionStarted = false;

try {
    $conn->begin_transaction();
    $transactionStarted = true;

    $logStmt = $conn->prepare("
        SELECT log_id, rfid_uid, actions
        FROM rfid_logs
        WHERE log_id = ?
        FOR UPDATE
    ");
    $logStmt->bind_param("i", $logId);
    $logStmt->execute();
    $log = $logStmt->get_result()->fetch_assoc();
    $logStmt->close();

    if (!$log) {
        transaction_fail(404, "Scan introuvable.");
    }

    if (strtoupper($log["rfid_uid"]) !== $uid) {
        transaction_fail(409, "Le scan ne correspond pas à cet outil.");
    }

    if (strtoupper($log["actions"]) !== "SCAN") {
        transaction_fail(409, "Ce scan a déjà été traité.");
    }

    $toolStmt = $conn->prepare("
        SELECT rfid_uid, part_number, serial_number, description_tool,
               last_check, next_check, status_
        FROM tools
        WHERE rfid_uid = ?
        FOR UPDATE
    ");
    $toolStmt->bind_param("s", $uid);
    $toolStmt->execute();
    $tool = $toolStmt->get_result()->fetch_assoc();
    $toolStmt->close();

    if (!$tool) {
        transaction_fail(404, "Outil introuvable.");
    }

    $employeeStmt = $conn->prepare("
        SELECT matricule, first_name, last_name, department, service
        FROM employees
        WHERE matricule = ?
        FOR SHARE
    ");
    $employeeStmt->bind_param("s", $matricule);
    $employeeStmt->execute();
    $employee = $employeeStmt->get_result()->fetch_assoc();
    $employeeStmt->close();

    if (!$employee) {
        transaction_fail(404, "Employé introuvable.");
    }

    $status = strtoupper($tool["status_"]);
    $transactionId = null;

    if ($action === "CHECK_OUT") {
        if ($status !== "AVAILABLE") {
            transaction_fail(409, "L'outil n'est plus disponible.");
        }

        $openStmt = $conn->prepare("
            SELECT transaction_id
            FROM transactions
            WHERE rfid_uid = ? AND return_date IS NULL
            FOR UPDATE
        ");
        $openStmt->bind_param("s", $uid);
        $openStmt->execute();
        $openResult = $openStmt->get_result();
        $openCount = $openResult->num_rows;
        $openStmt->close();

        if ($openCount !== 0) {
            transaction_fail(409, "Une transaction ouverte existe déjà pour cet outil.");
        }

        $insert = $conn->prepare("
            INSERT INTO transactions (rfid_uid, matricule, borrow_date, return_date)
            VALUES (?, ?, NOW(), NULL)
        ");
        $insert->bind_param("ss", $uid, $matricule);
        $insert->execute();

        if ($insert->affected_rows !== 1) {
            transaction_fail(409, "Le prêt n'a pas pu être enregistré.");
        }

        $transactionId = $conn->insert_id;
        $insert->close();

        $toolUpdate = $conn->prepare("
            UPDATE tools
            SET status_ = 'BORROWED'
            WHERE rfid_uid = ? AND status_ = 'AVAILABLE'
        ");
        $toolUpdate->bind_param("s", $uid);
        $toolUpdate->execute();

        if ($toolUpdate->affected_rows !== 1) {
            transaction_fail(409, "Le statut de l'outil a changé.");
        }

        $toolUpdate->close();
        $newStatus = "BORROWED";
    } else {
        if ($status !== "BORROWED") {
            transaction_fail(409, "L'outil n'est pas actuellement emprunté.");
        }

        $openStmt = $conn->prepare("
            SELECT transaction_id, matricule
            FROM transactions
            WHERE rfid_uid = ? AND return_date IS NULL
            FOR UPDATE
        ");
        $openStmt->bind_param("s", $uid);
        $openStmt->execute();
        $openResult = $openStmt->get_result();

        if ($openResult->num_rows !== 1) {
            $openStmt->close();
            transaction_fail(409, "La transaction ouverte de cet outil est incohérente.");
        }

        $openTransaction = $openResult->fetch_assoc();
        $openStmt->close();

        if (strtoupper($openTransaction["matricule"]) !== $matricule) {
            transaction_fail(409, "Le matricule ne correspond pas à l'emprunteur.");
        }

        $transactionId = (int) $openTransaction["transaction_id"];
        $returnUpdate = $conn->prepare("
            UPDATE transactions
            SET return_date = NOW()
            WHERE transaction_id = ? AND return_date IS NULL
        ");
        $returnUpdate->bind_param("i", $transactionId);
        $returnUpdate->execute();

        if ($returnUpdate->affected_rows !== 1) {
            transaction_fail(409, "Le retour a déjà été traité.");
        }

        $returnUpdate->close();

        $toolUpdate = $conn->prepare("
            UPDATE tools
            SET status_ = 'AVAILABLE'
            WHERE rfid_uid = ? AND status_ = 'BORROWED'
        ");
        $toolUpdate->bind_param("s", $uid);
        $toolUpdate->execute();

        if ($toolUpdate->affected_rows !== 1) {
            transaction_fail(409, "Le statut de l'outil a changé.");
        }

        $toolUpdate->close();
        $newStatus = "AVAILABLE";
    }

    $logUpdate = $conn->prepare("
        UPDATE rfid_logs
        SET actions = ?
        WHERE log_id = ? AND rfid_uid = ? AND actions = 'SCAN'
    ");
    $logUpdate->bind_param("sis", $action, $logId, $uid);
    $logUpdate->execute();

    if ($logUpdate->affected_rows !== 1) {
        transaction_fail(409, "Ce scan a déjà été confirmé.");
    }

    $logUpdate->close();
    $conn->commit();
    $transactionStarted = false;

    $tool["status_"] = $newStatus;

    transaction_response(200, [
        "success" => true,
        "log_id" => (int) $logId,
        "transaction_id" => (int) $transactionId,
        "action" => $action,
        "tool" => $tool,
        "employee" => $employee
    ]);
} catch (ApiTransactionException $error) {
    if ($transactionStarted) {
        $conn->rollback();
    }

    transaction_response($error->status, [
        "success" => false,
        "message" => $error->getMessage()
    ]);
} catch (Throwable $error) {
    if ($transactionStarted) {
        $conn->rollback();
    }

    transaction_response(500, [
        "success" => false,
        "message" => "La transaction n'a pas pu être finalisée."
    ]);
}
