-- This file only creates empty tables. Do not put real employee data here.

CREATE DATABASE IF NOT EXISTS rfid_aircraft_tools
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE rfid_aircraft_tools;

-- Employees who can check tools out and return them.
CREATE TABLE IF NOT EXISTS employees (
    matricule VARCHAR(20) PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    department VARCHAR(100),
    service VARCHAR(70),
    email VARCHAR(100)
) ENGINE=InnoDB;

-- Tools identified by their RFID UID.
CREATE TABLE IF NOT EXISTS tools (
    rfid_uid VARCHAR(50) PRIMARY KEY,
    part_number VARCHAR(50) NOT NULL,
    serial_number VARCHAR(50) UNIQUE NOT NULL,
    description_tool VARCHAR(255) NOT NULL,
    last_check DATE NOT NULL,
    next_check DATE NOT NULL,
    status_ ENUM(
        'AVAILABLE',
        'BORROWED',
        'MAINTENANCE',
        'CALIBRATION_DUE'
    ) NOT NULL DEFAULT 'AVAILABLE'
) ENGINE=InnoDB;

-- One row for each checkout, with the return date added later.
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    rfid_uid VARCHAR(50) NOT NULL,
    matricule VARCHAR(20) NOT NULL,
    borrow_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    return_date DATETIME NULL,
    INDEX idx_transactions_tool (rfid_uid),
    INDEX idx_transactions_employee (matricule),
    CONSTRAINT fk_transactions_tool
        FOREIGN KEY (rfid_uid) REFERENCES tools(rfid_uid),
    CONSTRAINT fk_transactions_employee
        FOREIGN KEY (matricule) REFERENCES employees(matricule)
) ENGINE=InnoDB;

-- Keep every RFID scan and the action confirmed by the user.
CREATE TABLE IF NOT EXISTS rfid_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    rfid_uid VARCHAR(50) NOT NULL,
    actions ENUM('SCAN', 'CHECK_OUT', 'CHECK_IN') NOT NULL DEFAULT 'SCAN',
    scan_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_rfid_logs_tool_time (rfid_uid, scan_time),
    CONSTRAINT fk_rfid_logs_tool
        FOREIGN KEY (rfid_uid) REFERENCES tools(rfid_uid)
) ENGINE=InnoDB;
