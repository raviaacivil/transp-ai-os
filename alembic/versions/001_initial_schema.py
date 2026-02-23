"""Initial schema for Transportation AI OS

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-02-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable required extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "postgis"')

    # ==========================================================================
    # ENUM TYPES
    # ==========================================================================
    op.execute("""
        CREATE TYPE project_status AS ENUM ('draft', 'active', 'submitted', 'archived')
    """)
    op.execute("""
        CREATE TYPE approach_direction AS ENUM ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW')
    """)
    op.execute("""
        CREATE TYPE movement_type AS ENUM ('L', 'T', 'R', 'LT', 'TR', 'LTR', 'U', 'LU')
    """)
    op.execute("""
        CREATE TYPE lane_type AS ENUM ('general', 'exclusive_left', 'exclusive_right', 'shared')
    """)
    op.execute("""
        CREATE TYPE signal_phase_type AS ENUM ('protected', 'permitted', 'protected_permitted', 'split', 'uncontrolled')
    """)
    op.execute("""
        CREATE TYPE volume_period AS ENUM ('am_peak', 'pm_peak', 'midday', 'weekend', 'daily')
    """)
    op.execute("""
        CREATE TYPE scenario_type AS ENUM ('existing', 'background', 'opening_year', 'horizon_year', 'mitigation', 'custom')
    """)
    op.execute("""
        CREATE TYPE change_operation AS ENUM ('create', 'update', 'delete')
    """)
    op.execute("""
        CREATE TYPE run_status AS ENUM ('pending', 'running', 'completed', 'failed')
    """)
    op.execute("""
        CREATE TYPE los_grade AS ENUM ('A', 'B', 'C', 'D', 'E', 'F')
    """)

    # ==========================================================================
    # PROJECTS
    # ==========================================================================
    op.execute("""
        CREATE TABLE projects (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            project_number VARCHAR(100),
            status project_status NOT NULL DEFAULT 'draft',
            client_name VARCHAR(255),
            jurisdiction VARCHAR(255),
            analyst_name VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX idx_projects_status ON projects(status) WHERE deleted_at IS NULL")
    op.execute("CREATE INDEX idx_projects_created_at ON projects(created_at DESC)")

    # ==========================================================================
    # NODES (Intersections)
    # ==========================================================================
    op.execute("""
        CREATE TABLE nodes (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            node_number INTEGER,
            geometry GEOMETRY(Point, 4326) NOT NULL,
            cycle_length_seconds INTEGER CHECK (cycle_length_seconds > 0 AND cycle_length_seconds <= 300),
            is_coordinated BOOLEAN DEFAULT FALSE,
            coordination_offset_seconds INTEGER DEFAULT 0,
            area_type VARCHAR(50) DEFAULT 'other',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_nodes_project_number UNIQUE (project_id, node_number)
        )
    """)
    op.execute("CREATE INDEX idx_nodes_geometry ON nodes USING GIST (geometry)")
    op.execute("CREATE INDEX idx_nodes_project_id ON nodes(project_id)")

    # ==========================================================================
    # APPROACHES
    # ==========================================================================
    op.execute("""
        CREATE TABLE approaches (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
            direction approach_direction NOT NULL,
            street_name VARCHAR(255),
            speed_limit_mph INTEGER CHECK (speed_limit_mph > 0 AND speed_limit_mph <= 100),
            grade_percent NUMERIC(5,2) DEFAULT 0,
            has_crosswalk BOOLEAN DEFAULT TRUE,
            conflicting_ped_volume_per_hour INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_approaches_node_direction UNIQUE (node_id, direction)
        )
    """)
    op.execute("CREATE INDEX idx_approaches_node_id ON approaches(node_id)")

    # ==========================================================================
    # LANE GROUPS
    # ==========================================================================
    op.execute("""
        CREATE TABLE lane_groups (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            approach_id UUID NOT NULL REFERENCES approaches(id) ON DELETE CASCADE,
            movement_type movement_type NOT NULL,
            lane_type lane_type NOT NULL DEFAULT 'general',
            num_lanes INTEGER NOT NULL CHECK (num_lanes > 0 AND num_lanes <= 10),
            lane_width_ft NUMERIC(5,2) DEFAULT 12.0,
            saturation_flow_rate INTEGER DEFAULT 1900,
            phase_type signal_phase_type NOT NULL DEFAULT 'protected',
            green_time_seconds INTEGER CHECK (green_time_seconds >= 0),
            yellow_time_seconds NUMERIC(4,1) DEFAULT 4.0,
            all_red_seconds NUMERIC(4,1) DEFAULT 1.0,
            right_turn_channelized BOOLEAN DEFAULT FALSE,
            right_turn_on_red_allowed BOOLEAN DEFAULT TRUE,
            left_turn_bay_length_ft INTEGER,
            heavy_vehicle_percent NUMERIC(5,2) DEFAULT 2.0,
            parking_maneuvers_per_hour INTEGER DEFAULT 0,
            bus_stops_per_hour INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_lane_groups_approach_id ON lane_groups(approach_id)")

    # ==========================================================================
    # VOLUMES
    # ==========================================================================
    op.execute("""
        CREATE TABLE volumes (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            lane_group_id UUID NOT NULL REFERENCES lane_groups(id) ON DELETE CASCADE,
            period volume_period NOT NULL,
            volume_vph INTEGER NOT NULL CHECK (volume_vph >= 0),
            peak_hour_factor NUMERIC(4,3) DEFAULT 0.92 CHECK (peak_hour_factor > 0 AND peak_hour_factor <= 1),
            count_date DATE,
            data_source VARCHAR(255),
            is_adjusted BOOLEAN DEFAULT FALSE,
            adjustment_notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_volumes_lane_group_period UNIQUE (lane_group_id, period)
        )
    """)
    op.execute("CREATE INDEX idx_volumes_lane_group_id ON volumes(lane_group_id)")

    # ==========================================================================
    # SCENARIOS
    # ==========================================================================
    op.execute("""
        CREATE TABLE scenarios (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            parent_scenario_id UUID REFERENCES scenarios(id) ON DELETE SET NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            scenario_type scenario_type NOT NULL,
            analysis_year INTEGER CHECK (analysis_year >= 1900 AND analysis_year <= 2100),
            is_locked BOOLEAN DEFAULT FALSE,
            locked_at TIMESTAMPTZ,
            locked_by VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_scenarios_project_name UNIQUE (project_id, name)
        )
    """)
    op.execute("CREATE INDEX idx_scenarios_project_id ON scenarios(project_id)")
    op.execute("CREATE INDEX idx_scenarios_parent_id ON scenarios(parent_scenario_id)")
    op.execute("CREATE INDEX idx_scenarios_type ON scenarios(scenario_type)")

    # ==========================================================================
    # SCENARIO CHANGES
    # ==========================================================================
    op.execute("""
        CREATE TABLE scenario_changes (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            scenario_id UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
            entity_type VARCHAR(50) NOT NULL,
            entity_id UUID NOT NULL,
            operation change_operation NOT NULL,
            change_data JSONB,
            change_reason TEXT,
            changed_by VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            sequence_number INTEGER NOT NULL DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX idx_scenario_changes_scenario_id ON scenario_changes(scenario_id)")
    op.execute("CREATE INDEX idx_scenario_changes_entity ON scenario_changes(entity_type, entity_id)")
    op.execute("CREATE INDEX idx_scenario_changes_sequence ON scenario_changes(scenario_id, sequence_number)")
    op.execute("CREATE INDEX idx_scenario_changes_data ON scenario_changes USING GIN (change_data)")

    # ==========================================================================
    # RUNS
    # ==========================================================================
    op.execute("""
        CREATE TABLE runs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            scenario_id UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
            engine_version VARCHAR(50) NOT NULL,
            input_hash VARCHAR(64) NOT NULL,
            status run_status NOT NULL DEFAULT 'pending',
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            error_message TEXT,
            error_details JSONB,
            input_snapshot JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_runs_scenario_hash UNIQUE (scenario_id, input_hash)
        )
    """)
    op.execute("CREATE INDEX idx_runs_scenario_id ON runs(scenario_id)")
    op.execute("CREATE INDEX idx_runs_status ON runs(status)")
    op.execute("CREATE INDEX idx_runs_created_at ON runs(created_at DESC)")
    op.execute("CREATE INDEX idx_runs_engine_version ON runs(engine_version)")

    # ==========================================================================
    # RESULTS - LANE GROUP LEVEL
    # ==========================================================================
    op.execute("""
        CREATE TABLE results_lane_group (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
            lane_group_id UUID NOT NULL REFERENCES lane_groups(id) ON DELETE CASCADE,
            volume_vph INTEGER NOT NULL,
            adjusted_saturation_flow INTEGER NOT NULL,
            green_ratio NUMERIC(5,4) NOT NULL,
            capacity_vph INTEGER NOT NULL,
            volume_to_capacity_ratio NUMERIC(6,4) NOT NULL,
            uniform_delay_seconds NUMERIC(8,2) NOT NULL,
            incremental_delay_seconds NUMERIC(8,2) NOT NULL,
            initial_queue_delay_seconds NUMERIC(8,2) DEFAULT 0,
            control_delay_seconds NUMERIC(8,2) NOT NULL,
            los los_grade NOT NULL,
            back_of_queue_50th_pct_ft NUMERIC(10,2),
            back_of_queue_95th_pct_ft NUMERIC(10,2),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_results_lane_group_run UNIQUE (run_id, lane_group_id)
        )
    """)
    op.execute("CREATE INDEX idx_results_lane_group_run_id ON results_lane_group(run_id)")
    op.execute("CREATE INDEX idx_results_lane_group_los ON results_lane_group(los)")

    # ==========================================================================
    # RESULTS - NODE LEVEL
    # ==========================================================================
    op.execute("""
        CREATE TABLE results_node (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
            node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
            total_entering_volume_vph INTEGER NOT NULL,
            intersection_capacity_utilization NUMERIC(6,4),
            average_control_delay_seconds NUMERIC(8,2) NOT NULL,
            los los_grade NOT NULL,
            worst_lane_group_id UUID REFERENCES lane_groups(id),
            worst_lane_group_vc_ratio NUMERIC(6,4),
            worst_lane_group_los los_grade,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_results_node_run UNIQUE (run_id, node_id)
        )
    """)
    op.execute("CREATE INDEX idx_results_node_run_id ON results_node(run_id)")
    op.execute("CREATE INDEX idx_results_node_los ON results_node(los)")

    # ==========================================================================
    # HELPER FUNCTION: Auto-update updated_at
    # ==========================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    # Apply triggers
    op.execute("""
        CREATE TRIGGER tr_projects_updated_at BEFORE UPDATE ON projects
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)
    op.execute("""
        CREATE TRIGGER tr_nodes_updated_at BEFORE UPDATE ON nodes
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)
    op.execute("""
        CREATE TRIGGER tr_approaches_updated_at BEFORE UPDATE ON approaches
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)
    op.execute("""
        CREATE TRIGGER tr_lane_groups_updated_at BEFORE UPDATE ON lane_groups
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)
    op.execute("""
        CREATE TRIGGER tr_volumes_updated_at BEFORE UPDATE ON volumes
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)
    op.execute("""
        CREATE TRIGGER tr_scenarios_updated_at BEFORE UPDATE ON scenarios
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)

    # ==========================================================================
    # VIEWS
    # ==========================================================================
    op.execute("""
        CREATE VIEW v_lane_groups_full AS
        SELECT
            lg.id AS lane_group_id,
            lg.movement_type,
            lg.num_lanes,
            lg.saturation_flow_rate,
            a.id AS approach_id,
            a.direction,
            a.street_name,
            n.id AS node_id,
            n.name AS node_name,
            n.node_number,
            n.geometry,
            p.id AS project_id,
            p.name AS project_name
        FROM lane_groups lg
        JOIN approaches a ON lg.approach_id = a.id
        JOIN nodes n ON a.node_id = n.id
        JOIN projects p ON n.project_id = p.id
        WHERE p.deleted_at IS NULL
    """)

    op.execute("""
        CREATE VIEW v_latest_run_results AS
        SELECT DISTINCT ON (r.scenario_id)
            r.id AS run_id,
            r.scenario_id,
            r.engine_version,
            r.input_hash,
            r.status,
            r.completed_at,
            s.name AS scenario_name,
            s.scenario_type
        FROM runs r
        JOIN scenarios s ON r.scenario_id = s.id
        WHERE r.status = 'completed'
        ORDER BY r.scenario_id, r.completed_at DESC
    """)


def downgrade() -> None:
    # Drop views
    op.execute("DROP VIEW IF EXISTS v_latest_run_results")
    op.execute("DROP VIEW IF EXISTS v_lane_groups_full")

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS tr_scenarios_updated_at ON scenarios")
    op.execute("DROP TRIGGER IF EXISTS tr_volumes_updated_at ON volumes")
    op.execute("DROP TRIGGER IF EXISTS tr_lane_groups_updated_at ON lane_groups")
    op.execute("DROP TRIGGER IF EXISTS tr_approaches_updated_at ON approaches")
    op.execute("DROP TRIGGER IF EXISTS tr_nodes_updated_at ON nodes")
    op.execute("DROP TRIGGER IF EXISTS tr_projects_updated_at ON projects")

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop tables (reverse order of creation due to FK constraints)
    op.execute("DROP TABLE IF EXISTS results_node")
    op.execute("DROP TABLE IF EXISTS results_lane_group")
    op.execute("DROP TABLE IF EXISTS runs")
    op.execute("DROP TABLE IF EXISTS scenario_changes")
    op.execute("DROP TABLE IF EXISTS scenarios")
    op.execute("DROP TABLE IF EXISTS volumes")
    op.execute("DROP TABLE IF EXISTS lane_groups")
    op.execute("DROP TABLE IF EXISTS approaches")
    op.execute("DROP TABLE IF EXISTS nodes")
    op.execute("DROP TABLE IF EXISTS projects")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS los_grade")
    op.execute("DROP TYPE IF EXISTS run_status")
    op.execute("DROP TYPE IF EXISTS change_operation")
    op.execute("DROP TYPE IF EXISTS scenario_type")
    op.execute("DROP TYPE IF EXISTS volume_period")
    op.execute("DROP TYPE IF EXISTS signal_phase_type")
    op.execute("DROP TYPE IF EXISTS lane_type")
    op.execute("DROP TYPE IF EXISTS movement_type")
    op.execute("DROP TYPE IF EXISTS approach_direction")
    op.execute("DROP TYPE IF EXISTS project_status")

    # Note: We don't drop uuid-ossp or postgis extensions
    # as they may be used by other schemas
