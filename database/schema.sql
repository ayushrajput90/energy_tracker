-- ============================================================
-- Renewable Energy Usage Tracker - Database Schema (MySQL)
-- ============================================================

CREATE DATABASE IF NOT EXISTS renewable_energy_db
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE renewable_energy_db;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. User Settings Table
CREATE TABLE IF NOT EXISTS user_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    electricity_tariff DECIMAL(10, 4) DEFAULT 0.1500, -- Tariff per kWh
    co2_emission_factor DECIMAL(10, 4) DEFAULT 0.8200, -- kg CO2 per kWh
    theme VARCHAR(20) DEFAULT 'light', -- 'light' or 'dark'
    currency_code VARCHAR(10) DEFAULT 'INR', -- 'INR', 'USD', 'EUR', 'GBP'
    currency_symbol VARCHAR(10) DEFAULT '₹', -- '₹', '$', '€', '£'
    notification_preferences BOOLEAN DEFAULT TRUE,
    unit_preference VARCHAR(10) DEFAULT 'kWh',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_settings_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Renewable Sources Configuration Table
CREATE TABLE IF NOT EXISTS renewable_sources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    source_type ENUM('Solar', 'Wind', 'Hydro', 'Biomass', 'Geothermal', 'Other Renewable') NOT NULL,
    installed_capacity_kw DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    expected_daily_generation_kwh DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    effective_from DATE NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_sources_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_sources_user_type (user_id, source_type),
    INDEX idx_sources_active (user_id, active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Source Capacity History Table (Historical Preservation)
CREATE TABLE IF NOT EXISTS source_capacity_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT NOT NULL,
    capacity_kw DECIMAL(10, 2) NOT NULL,
    expected_daily_generation_kwh DECIMAL(10, 2) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_capacity_history_source FOREIGN KEY (source_id) REFERENCES renewable_sources(id) ON DELETE CASCADE,
    INDEX idx_capacity_hist_source (source_id),
    INDEX idx_capacity_hist_dates (source_id, effective_from, effective_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Daily Generation Overrides Table (Manual Daily Overrides)
CREATE TABLE IF NOT EXISTS daily_generation_overrides (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    source_id INT NOT NULL,
    date DATE NOT NULL,
    automatic_generation_kwh DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    override_generation_kwh DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    reason VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_overrides_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_overrides_source FOREIGN KEY (source_id) REFERENCES renewable_sources(id) ON DELETE CASCADE,
    INDEX idx_overrides_user_date (user_id, date),
    INDEX idx_overrides_source_date (source_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Energy Records Table
-- CRITICAL REQUIREMENT:
-- Multiple records for the same user, same date, and same source are explicitly permitted.
-- NO UNIQUE CONSTRAINT on (user_id, date) or (user_id, date, renewable_source).
CREATE TABLE IF NOT EXISTS energy_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    source_id INT NULL,
    date DATE NOT NULL,
    renewable_source ENUM('Solar', 'Wind', 'Hydro', 'Biomass', 'Geothermal', 'Other Renewable') NOT NULL,
    energy_generated_kwh DECIMAL(12, 4) NOT NULL DEFAULT 0.0000,
    renewable_energy_consumed_kwh DECIMAL(12, 4) NOT NULL DEFAULT 0.0000,
    grid_energy_consumed_kwh DECIMAL(12, 4) NOT NULL DEFAULT 0.0000,
    total_energy_consumed_kwh DECIMAL(12, 4) NOT NULL DEFAULT 0.0000,
    electricity_tariff DECIMAL(10, 4) NOT NULL DEFAULT 0.1500,
    is_override BOOLEAN NOT NULL DEFAULT FALSE,
    automatic_generation_kwh DECIMAL(12, 4) NOT NULL DEFAULT 0.0000,
    override_generation_kwh DECIMAL(12, 4) NULL,
    storage_used_kwh DECIMAL(12, 4) NOT NULL DEFAULT 0.0000,
    surplus_kwh DECIMAL(12, 4) NOT NULL DEFAULT 0.0000,
    storage_balance_kwh DECIMAL(12, 4) NOT NULL DEFAULT 0.0000,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_energy_records_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_energy_records_source FOREIGN KEY (source_id) REFERENCES renewable_sources(id) ON DELETE SET NULL,
    INDEX idx_energy_user_date (user_id, date),
    INDEX idx_energy_user_source (user_id, renewable_source),
    INDEX idx_energy_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Renewable Energy Storage Transactions Table (Ledger)
CREATE TABLE IF NOT EXISTS renewable_storage_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    date DATE NOT NULL,
    source_id INT NULL,
    transaction_type ENUM('SURPLUS', 'CONSUME', 'ADJUSTMENT') NOT NULL,
    amount_kwh DECIMAL(12, 4) NOT NULL,
    reference_record_id INT NULL,
    notes VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_storage_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_storage_source FOREIGN KEY (source_id) REFERENCES renewable_sources(id) ON DELETE SET NULL,
    CONSTRAINT fk_storage_record FOREIGN KEY (reference_record_id) REFERENCES energy_records(id) ON DELETE SET NULL,
    INDEX idx_storage_user_date (user_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Goals Table
CREATE TABLE IF NOT EXISTS goals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    goal_type ENUM(
        'Energy Generation',
        'Renewable Consumption',
        'Renewable Percentage',
        'CO2 Reduction/Avoidance',
        'Grid Electricity Displacement',
        'Cost Savings'
    ) NOT NULL,
    target_value DECIMAL(12, 2) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    description VARCHAR(255) NULL,
    status ENUM('Active', 'Completed', 'Expired') DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_goals_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_goals_user (user_id),
    INDEX idx_goals_dates (start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Activities Table (Audit & Log)
CREATE TABLE IF NOT EXISTS activities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    description VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_activities_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_activities_user (user_id),
    INDEX idx_activities_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
