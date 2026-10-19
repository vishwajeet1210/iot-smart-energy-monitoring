"""
Unit and configuration tests for AWS Sydney to Mumbai migration readiness.
Validates file presence, HCL variables, region parameterization,
least-privilege security settings, and state isolation.
"""

import os
import re
import shutil
import subprocess
import tempfile
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TERRAFORM_DIR = os.path.join(ROOT_DIR, "terraform")
MUMBAI_TF_DIR = os.path.join(TERRAFORM_DIR, "mumbai")
JENKINSFILE_PATH = os.path.join(ROOT_DIR, "Jenkinsfile")


class TestMumbaiTerraformStructure:
    """Verifies the separate Mumbai Terraform directory structure and file integrity."""

    def test_mumbai_directory_exists(self):
        assert os.path.isdir(MUMBAI_TF_DIR), "terraform/mumbai/ directory must exist"

    def test_required_terraform_files_present(self):
        required_files = [
            "versions.tf",
            "provider.tf",
            "variables.tf",
            "main.tf",
            "outputs.tf",
            "terraform.tfvars.example",
            "terraform.tfvars",
        ]
        for fname in required_files:
            fpath = os.path.join(MUMBAI_TF_DIR, fname)
            assert os.path.isfile(fpath), f"Required file '{fname}' missing in terraform/mumbai/"

    def test_no_hardcoded_sydney_references_in_mumbai_config(self):
        """Ensures terraform/mumbai has no hardcoded references to Sydney region, IP, or EC2 ID."""
        sydney_patterns = [
            r"ap-southeast-2",
            r"13\.210\.96\.204",
            r"i-06e85f034d1c71c9c",
            r"subnet-0db7732a9d0454372",
            r"vpc-05713fbc5a8c9ed52",
        ]
        for fname in os.listdir(MUMBAI_TF_DIR):
            if fname.endswith(".tf") or fname.endswith(".tfvars"):
                fpath = os.path.join(MUMBAI_TF_DIR, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                for pat in sydney_patterns:
                    matches = re.findall(pat, content)
                    assert not matches, (
                        f"Found forbidden Sydney reference '{pat}' in {fname}"
                    )

    def test_mumbai_ami_matches_ubuntu_jammy_canonical(self):
        """Verifies Mumbai AMI data source looks up Ubuntu 22.04 LTS (Jammy) from Canonical."""
        main_tf = os.path.join(MUMBAI_TF_DIR, "main.tf")
        with open(main_tf, "r", encoding="utf-8") as f:
            content = f.read()
        assert "099720109477" in content, "Canonical AWS Account ID (099720109477) must be AMI owner"
        assert "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" in content, (
            "AMI filter must target Ubuntu Jammy 22.04 LTS amd64 server"
        )


class TestMumbaiSecurityAndLeastPrivilege:
    """Validates security controls in the Mumbai Terraform architecture."""

    def test_iam_role_name_is_region_differentiated(self):
        """Ensures IAM role name does not collide with Sydney's account-wide role."""
        main_tf = os.path.join(MUMBAI_TF_DIR, "main.tf")
        with open(main_tf, "r", encoding="utf-8") as f:
            content = f.read()
        assert "${var.project_name}-mumbai-ec2-role" in content or "smart-energy-monitor-mumbai-ec2-role" in content, (
            "IAM role in Mumbai must have region-differentiated name to prevent account-wide collision"
        )

    def test_imdsv2_is_enforced(self):
        """Ensures IMDSv2 token requirement is strictly enforced on EC2."""
        main_tf = os.path.join(MUMBAI_TF_DIR, "main.tf")
        with open(main_tf, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'http_tokens                 = "required"' in content, (
            "IMDSv2 http_tokens must be set to 'required'"
        )

    def test_vpc_cidr_avoids_sydney_overlap(self):
        """Ensures Mumbai VPC uses 10.1.0.0/16 to avoid collision with Sydney 10.0.0.0/16."""
        vars_tf = os.path.join(MUMBAI_TF_DIR, "variables.tf")
        with open(vars_tf, "r", encoding="utf-8") as f:
            content = f.read()
        assert "10.1.0.0/16" in content, "Mumbai VPC CIDR must default to 10.1.0.0/16"

    def test_ssh_disabled_by_default(self):
        """Ensures SSH port 22 is disabled by default."""
        vars_tf = os.path.join(MUMBAI_TF_DIR, "variables.tf")
        with open(vars_tf, "r", encoding="utf-8") as f:
            content = f.read()
        assert "default     = false" in content and "enable_ssh" in content, (
            "enable_ssh must default to false"
        )


class TestJenkinsfileMumbaiOnlyTargeting:
    """Validates Jenkinsfile enforces AWS Mumbai as the sole permitted deployment target."""

    def test_jenkinsfile_has_mumbai_only_deploy_region_parameter(self):
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "DEPLOY_REGION" in content, "Jenkinsfile must declare DEPLOY_REGION parameter"
        assert "choices: ['ap-south-1']" in content, "DEPLOY_REGION choices must only permit ap-south-1"

    def test_declarative_options_block_restored(self):
        """Verifies declarative options block specifies 30-minute timeout and build log discarder."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "options {" in content, "Jenkinsfile must declare pipeline options block"
        assert "timeout(time: 30, unit: 'MINUTES')" in content, (
            "Options block must specify timeout of 30 MINUTES"
        )
        assert "buildDiscarder(logRotator(numToKeepStr: '10'))" in content, (
            "Options block must specify buildDiscarder keeping 10 builds"
        )

    def test_jenkinsfile_fail_fast_rejects_non_mumbai_regions(self):
        """Ensures non-mumbai regions are rejected by fail-fast gate."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "selectedRegion != 'ap-south-1'" in content, (
            "Jenkinsfile must contain fail-fast check rejecting selectedRegion != 'ap-south-1'"
        )
        assert "error(\"❌ Deployment Gate Failure: Target region '${selectedRegion}' is rejected." in content

    def test_mumbai_defaults_declared(self):
        """Verifies Mumbai defaults for instance, app URL, ECR registry, and Terraform directory."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "i-07025008dd9b165a8" in content, "Mumbai EC2 instance default i-07025008dd9b165a8 must be present"
        assert "http://3.110.85.209:8501" in content, "Mumbai App URL default http://3.110.85.209:8501 must be present"
        assert "695496430374.dkr.ecr.ap-south-1.amazonaws.com" in content, "Mumbai ECR registry must be present"
        assert "TF_WORKING_DIR           = 'terraform/mumbai'" in content or "TF_WORKING_DIR  = 'terraform/mumbai'" in content, (
            "Terraform working directory must default to terraform/mumbai"
        )

    def test_no_sydney_deployment_fallback_in_jenkinsfile(self):
        """Ensures all deployment fallback to Sydney (ap-southeast-2, instance i-06e85f034d1c71c9c, IP) is removed."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        forbidden_sydney_patterns = [
            "ap-southeast-2",
            "i-06e85f034d1c71c9c",
            "13.210.96.204",
        ]
        for pat in forbidden_sydney_patterns:
            assert pat not in content, f"Forbidden Sydney reference '{pat}' found in Jenkinsfile"

    def test_deploy_stage_validates_instance_id_before_ssm(self):
        """Ensures stage 6 fails safely if target EC2 instance ID is empty."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "!env.EC2_INSTANCE_ID" in content or "EC2_INSTANCE_ID.trim() == ''" in content, (
            "Jenkinsfile must check for non-empty EC2_INSTANCE_ID before SSM dispatch"
        )

    def test_deployment_safety_and_rollback_logic_present(self):
        """Ensures image is validated prior to replacement and rollback logic exists."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "docker image inspect" in content, "Jenkinsfile must inspect pulled image before replacing running container"
        assert "-backup" in content, "Jenkinsfile must back up running container before starting replacement"
        assert "Restoring previous working container" in content, "Jenkinsfile must include rollback restoration"

    def test_target_validation_rejects_foreign_parameters(self):
        """Ensures Jenkinsfile rejects foreign regions, EC2 instance IDs, ECR registries, or URLs."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "selectedInstance != 'i-07025008dd9b165a8'" in content, (
            "Pipeline must reject any EC2 instance ID other than Mumbai instance i-07025008dd9b165a8"
        )
        assert "selectedRegistry != '695496430374.dkr.ecr.ap-south-1.amazonaws.com'" in content, (
            "Pipeline must reject any ECR registry other than Mumbai registry"
        )
        assert "selectedUrl != 'http://3.110.85.209:8501'" in content, (
            "Pipeline must reject any application URL other than Mumbai URL"
        )
        assert "env.EC2_INSTANCE_ID != 'i-07025008dd9b165a8'" in content, (
            "Deploy stage must gate against non-Mumbai instance"
        )
        assert "env.AWS_REGION != 'ap-south-1'" in content, (
            "Deploy stage must gate against non-Mumbai AWS region"
        )
        assert "env.ECR_REGISTRY != '695496430374.dkr.ecr.ap-south-1.amazonaws.com'" in content, (
            "Deploy stage must gate against non-Mumbai ECR registry"
        )
        assert "env.APP_URL != 'http://3.110.85.209:8501'" in content, (
            "Deploy stage must gate against non-Mumbai app URL"
        )

    def test_deployment_ordering_image_validated_before_stopping_container(self):
        """Ensures the new image is pulled and inspected before the active container is stopped."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        pull_idx = content.find("docker pull")
        inspect_idx = content.find("docker image inspect")
        stop_old_idx = content.find("Stopping and preserving current container as staged backup...")

        assert pull_idx != -1 and inspect_idx != -1 and stop_old_idx != -1
        assert pull_idx < inspect_idx < stop_old_idx, (
            "Image must be pulled and validated before stopping the running container"
        )

    def test_staged_backup_preserves_container_before_deleting_old_backup(self):
        """Ensures old backup is not deleted until current container is safely staged as newbackup and recovery state set."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        stage_backup_idx = content.find("docker rename ${env.APP_NAME} ${env.APP_NAME}-newbackup")
        backup_preserved_idx = content.find("BACKUP_PRESERVED=1")
        rm_old_backup_idx = content.find("docker rm -f ${env.APP_NAME}-backup")
        promote_backup_idx = content.find("docker rename ${env.APP_NAME}-newbackup ${env.APP_NAME}-backup")

        assert stage_backup_idx != -1 and backup_preserved_idx != -1 and rm_old_backup_idx != -1 and promote_backup_idx != -1
        assert stage_backup_idx < backup_preserved_idx < rm_old_backup_idx < promote_backup_idx, (
            "Recovery state BACKUP_PRESERVED=1 must be set immediately after newbackup is created, before removing old backup"
        )

    def test_backup_rotation_prefers_newbackup_over_old_backup(self):
        """Ensures rollback prefers newly preserved newbackup container over older backup."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        inspect_newbackup_idx = content.find("if docker inspect ${env.APP_NAME}-newbackup >/dev/null 2>&1; then TARGET_BACKUP='${env.APP_NAME}-newbackup'")
        inspect_oldbackup_idx = content.find("elif docker inspect ${env.APP_NAME}-backup >/dev/null 2>&1; then TARGET_BACKUP='${env.APP_NAME}-backup'")
        assert inspect_newbackup_idx != -1 and inspect_oldbackup_idx != -1
        assert inspect_newbackup_idx < inspect_oldbackup_idx, (
            "Rollback must evaluate and prefer newbackup before old backup"
        )

    def test_backup_retained_until_after_finalization_and_deploy_success_ordered_before_cleanup(self):
        """Verifies backup container is retained through finalization, and DEPLOY_SUCCESS=1 is set before cleanup."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        docker_health_idx = content.find("Awaiting Docker container health check")
        http_health_idx = content.find("Verifying final local HTTP health check against http://localhost:8501/_stcore/health")
        inspect_running_idx = content.find("docker inspect --format='Image: {{.Config.Image}}")
        inspect_volume_idx = content.find("ls -la /var/data/energy")
        deploy_success_idx = content.find("DEPLOY_SUCCESS=1")
        cleanup_backup_idx = content.find("Cleaning up backup container(s)...")

        assert docker_health_idx != -1 and http_health_idx != -1
        assert inspect_running_idx != -1 and inspect_volume_idx != -1
        assert deploy_success_idx != -1 and cleanup_backup_idx != -1

        assert docker_health_idx < http_health_idx < inspect_running_idx < inspect_volume_idx < deploy_success_idx < cleanup_backup_idx, (
            "Backup container must be retained through health checks and finalization verification; "
            "DEPLOY_SUCCESS=1 must be set once deployment is committed, before backup cleanup"
        )

    def test_failures_trigger_guarded_rollback(self):
        """Ensures startup failure, Docker health failure, and HTTP health failure all trigger guarded rollback."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # Check guarded rollback function definition
        assert "rollback()" in content, "A guarded rollback function must be defined"
        assert "docker stop ${env.APP_NAME} >/dev/null 2>&1 || true" in content, (
            "Rollback stop command must be guarded with || true"
        )
        assert "docker rm -f ${env.APP_NAME} >/dev/null 2>&1 || true" in content, (
            "Rollback rm command must be guarded with || true"
        )

        # Check that all 3 failure points trigger rollback
        assert "! docker run" in content and "rollback; exit 1" in content, (
            "Container startup failure must trigger rollback"
        )
        assert "HEALTHY" in content and "Replacement container failed Docker health check" in content, (
            "Docker health check failure must trigger rollback"
        )
        assert "HTTP_OK" in content and "Final local HTTP health check failed" in content, (
            "HTTP health check failure must trigger rollback"
        )

    def test_rollback_verifies_health_and_does_not_suppress_errors(self):
        """Ensures rollback checks for rename/start failures and verifies restored container becomes healthy."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify restoration errors are NOT suppressed with || true
        assert "! docker rename \\\"\\$TARGET_BACKUP\\\" ${env.APP_NAME}" in content, (
            "Rollback must check docker rename exit code and not suppress failures"
        )
        assert "! docker start ${env.APP_NAME}" in content, (
            "Rollback must check docker start exit code and not suppress failures"
        )

        # Verify health check verification on restored container
        assert "Awaiting health check on restored container ${env.APP_NAME}" in content, (
            "Rollback must wait for restored container to become healthy"
        )
        assert "R_STATUS=\\$(docker inspect --format='{{.State.Health.Status}}' ${env.APP_NAME}" in content, (
            "Rollback must inspect health status of restored container"
        )
        assert "http://localhost:8501/_stcore/health" in content, (
            "Rollback must verify HTTP health check on restored container"
        )
        assert "CRITICAL: Rollback verification failed - restored container failed health check" in content
        assert "CRITICAL: Rollback verification failed - restored container failed HTTP health check" in content

    def test_rollback_preserves_recovery_container_on_failure(self):
        """Ensures rollback does not discard recovery container if restoration fails."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert r"Recovery container \$TARGET_BACKUP preserved." in content
        assert "Recovery container preserved." in content
        assert "ROLLBACK_SUCCESS=1" in content

    def test_interrupted_deployment_triggers_rollback_via_trap(self):
        """Ensures shell EXIT trap triggers rollback on unexpected failure and avoids repeated loops."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "trap " in content and "EXIT" in content, "Deployment script must register an EXIT trap"
        assert "BACKUP_PRESERVED" in content and "DEPLOY_SUCCESS" in content, (
            "EXIT trap must monitor BACKUP_PRESERVED and DEPLOY_SUCCESS flags"
        )
        assert r"\"\$ROLLBACK_TRIGGERED\" -eq 0" in content, (
            "EXIT trap must guard rollback execution against repeated loops"
        )
        assert r"exit \$EXIT_CODE" in content, (
            "EXIT trap must propagate original failure exit code"
        )
        assert "CRITICAL: Deployment failed and rollback was unsuccessful" in content, (
            "EXIT trap must report loudly if rollback was unsuccessful"
        )

    def test_database_volume_persistence_preserved(self):
        """Ensures persistent storage volume /var/data/energy is mounted and preserved."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "-v /var/data/energy:/app/data" in content, "Pipeline must preserve volume mount /var/data/energy:/app/data"
        assert "-e ENERGY_DB_PATH=/app/data/energy.db" in content, "Pipeline must preserve SQLite database path"

    def test_first_deployment_without_previous_container_handles_failure_cleanly(self):
        """Ensures that on a fresh host with no prior container, failure logs cleanly without invalid rename/restore."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "No backup container to restore (first deployment without previous container)" in content, (
            "Rollback routine must detect absence of backup container and log cleanly"
        )

    def test_ssm_command_polling_timeout_provides_adequate_headroom(self):
        """Ensures SSM polling loop duration (>150s) comfortably exceeds deployment, healthcheck, and rollback duration."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        # Verify 35 iterations x 5s polling is configured in both sh and powershell blocks
        assert "seq 1 35" in content, "Unix SSM polling must use 35 iterations"
        assert "$i -le 35" in content, "PowerShell SSM polling must use 35 iterations"
        assert "sleep 5" in content, "Unix SSM polling loop must sleep 5s between polls"
        assert "Start-Sleep -Seconds 5" in content, "PowerShell SSM polling loop must sleep 5s between polls"

    def test_zero_sydney_references_throughout_entire_pipeline(self):
        """Ensures zero occurrences of Sydney region, instance ID, IP, or names across the entire Jenkinsfile."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        forbidden_terms = ["ap-southeast-2", "i-06e85f034d1c71c9c", "13.210.96.204", "Sydney", "sydney"]
        for term in forbidden_terms:
            assert term not in content, f"Forbidden Sydney term '{term}' found in Jenkinsfile"



class TestStateIsolation:
    """Verifies that Sydney state is preserved and not modified."""

    def test_sydney_state_file_exists_and_references_sydney(self):
        sydney_state = os.path.join(TERRAFORM_DIR, "terraform.tfstate")
        assert os.path.isfile(sydney_state), "Sydney terraform.tfstate must exist"
        with open(sydney_state, "r", encoding="utf-8") as f:
            content = f.read()
        assert "ap-southeast-2" in content, "Sydney state must reference ap-southeast-2"
        assert "i-06e85f034d1c71c9c" in content, "Sydney state must reference instance i-06e85f034d1c71c9c"


def extract_ssm_script(content):
    m = re.search(r'def ssmCommands = \[(.*?)\]\s+def ssmParamsJson', content, re.DOTALL)
    if not m:
        raise ValueError("ssmCommands not found in Jenkinsfile")
    block = m.group(1)
    lines = []
    for line in block.strip().splitlines():
        line = line.strip()
        if (line.startswith('"') and line.endswith('",')) or (line.startswith('"') and line.endswith('"')):
            c = line.rstrip(',')[1:-1]
            c = c.replace('\\"', '"').replace('\\$', '$')
            c = c.replace('${env.APP_NAME}', 'smart-energy-monitor')
            c = c.replace('${env.AWS_REGION}', 'ap-south-1')
            c = c.replace('${env.ECR_REGISTRY}', '695496430374.dkr.ecr.ap-south-1.amazonaws.com')
            c = c.replace('${env.ECR_REPO}', 'smart-energy-monitor')
            c = c.replace('${env.IMAGE_TAG}', 'latest')
            lines.append(c)
    return "\n".join(lines)


def run_deployment_simulation(env_overrides=None, initial_containers=None):
    if not shutil.which("bash"):
        pytest.skip("bash is required for behavioral simulation")

    with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    raw_script = extract_ssm_script(content)

    with tempfile.TemporaryDirectory() as td:
        wsl_state_dir = os.path.join(td, "containers").replace("\\", "/")
        if wsl_state_dir.startswith("C:") or wsl_state_dir.startswith("c:"):
            wsl_state_dir = "/mnt/c" + wsl_state_dir[2:]
        state_dir = os.path.join(td, "containers")
        os.makedirs(state_dir, exist_ok=True)

        wsl_data_dir = os.path.join(td, "data").replace("\\", "/")
        if wsl_data_dir.startswith("C:") or wsl_data_dir.startswith("c:"):
            wsl_data_dir = "/mnt/c" + wsl_data_dir[2:]
        data_dir = os.path.join(td, "data")
        os.makedirs(data_dir, exist_ok=True)

        if initial_containers:
            for c in initial_containers:
                with open(os.path.join(state_dir, c), "w", encoding="utf-8") as f:
                    f.write("running")

        mock_header = f"""
STATE_DIR="{wsl_state_dir}"
mkdir -p "{wsl_data_dir}" 2>/dev/null || true

sleep() {{
    return 0
}}

aws() {{
    if [ "$MOCK_FAIL_AWS" = "1" ]; then return 1; fi
    return 0
}}

curl() {{
    if [ "$MOCK_RESTORE_HTTP_FAIL" = "1" ] && [ "$ROLLBACK_TRIGGERED" = "1" ]; then
        return 1
    elif [ "$MOCK_FAIL_HTTP" = "1" ] && [ "$ROLLBACK_TRIGGERED" != "1" ]; then
        return 1
    fi
    return 0
}}

docker() {{
    cmd="$1"
    case "$cmd" in
        login|pull)
            return 0
            ;;
        image)
            return 0
            ;;
        logs)
            echo "mock logs"
            return 0
            ;;
        inspect)
            if [[ "$*" == *Health.Status* ]]; then
                if [ "$MOCK_RESTORE_HEALTH_FAIL" = "1" ] && [ "$ROLLBACK_TRIGGERED" = "1" ]; then
                    echo "unhealthy"
                elif [ "$MOCK_HEALTH_FAIL" = "1" ] && [ "$ROLLBACK_TRIGGERED" != "1" ]; then
                    echo "unhealthy"
                else
                    echo "healthy"
                fi
                return 0
            elif [[ "$*" == *--format* ]]; then
                echo "mock formatted info"
                return 0
            else
                target="$2"
                if [ -f "$STATE_DIR/$target" ]; then
                    return 0
                fi
                return 1
            fi
            ;;
        stop)
            target="$2"
            if [ "$MOCK_FAIL_STOP" = "1" ]; then return 1; fi
            if [ -f "$STATE_DIR/$target" ]; then
                echo "stopped" > "$STATE_DIR/$target"
                return 0
            fi
            return 1
            ;;
        rename)
            src="$2"; dst="$3"
            if [ "$MOCK_FAIL_RENAME_NEWBACKUP" = "1" ] && [ "$dst" = "smart-energy-monitor-newbackup" ]; then return 1; fi
            if [ "$MOCK_FAIL_PROMOTION" = "1" ] && [ "$dst" = "smart-energy-monitor-backup" ]; then return 1; fi
            if [ "$MOCK_FAIL_RESTORE_RENAME" = "1" ] && [ "$dst" = "smart-energy-monitor" ]; then return 1; fi
            if [ -f "$STATE_DIR/$src" ]; then
                mv "$STATE_DIR/$src" "$STATE_DIR/$dst"
                return 0
            fi
            return 1
            ;;
        rm)
            target="$3"
            if [ "$target" = "" ]; then target="$2"; fi
            if [ "$MOCK_FAIL_RM_BACKUP" = "1" ] && [ "$target" = "smart-energy-monitor-backup" ]; then return 1; fi
            if [ "$MOCK_FAIL_CLEANUP" = "1" ] && [ "$DEPLOY_SUCCESS" = "1" ]; then return 1; fi
            rm -f "$STATE_DIR/$target"
            return 0
            ;;
        start)
            target="$2"
            if [ "$MOCK_FAIL_RESTORE_START" = "1" ]; then return 1; fi
            if [ -f "$STATE_DIR/$target" ]; then
                echo "running" > "$STATE_DIR/$target"
                return 0
            fi
            return 1
            ;;
        run)
            if [ "$MOCK_FAIL_RUN" = "1" ]; then return 1; fi
            echo "running" > "$STATE_DIR/smart-energy-monitor"
            return 0
            ;;
    esac
}}
"""
        env_prefix = ""
        if env_overrides:
            env_prefix = "\n".join([f'export {k}="{v}"' for k, v in env_overrides.items()]) + "\n"

        full_script = env_prefix + mock_header + "\n" + raw_script.replace("/var/data/energy", wsl_data_dir)
        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)

        res = subprocess.run(["bash"], input=full_script.encode("utf-8"), capture_output=True, env=env)
        stdout = res.stdout.decode("utf-8", errors="replace")
        stderr = res.stderr.decode("utf-8", errors="replace")
        active_containers = os.listdir(state_dir)
        return res.returncode, stdout, stderr, active_containers


class TestDeploymentRollbackBehavioral:
    """Executable regression tests validating backup rotation and rollback failure boundaries."""

    def test_happy_path_deployment(self):
        """Happy path: active container rotated, replacement verified healthy, backup cleaned up."""
        rc, stdout, stderr, containers = run_deployment_simulation(
            initial_containers=["smart-energy-monitor"]
        )
        assert rc == 0
        assert "smart-energy-monitor" in containers
        assert "smart-energy-monitor-backup" not in containers
        assert "smart-energy-monitor-newbackup" not in containers
        assert "Deployment finalized successfully." in stdout

    def test_replacement_run_failure_triggers_rollback(self):
        """When docker run fails, rollback triggers, restores previous container, and exits nonzero."""
        rc, stdout, stderr, containers = run_deployment_simulation(
            env_overrides={"MOCK_FAIL_RUN": "1"},
            initial_containers=["smart-energy-monitor"]
        )
        assert rc == 1
        assert "smart-energy-monitor" in containers
        assert "ERROR: Failed to launch replacement container." in stdout
        assert "Initiating rollback to previous working container..." in stdout
        assert "Previous working container successfully restored" in stdout

    def test_docker_health_failure_triggers_rollback(self):
        """When replacement fails Docker health check, rollback restores previous container and exits nonzero."""
        rc, stdout, stderr, containers = run_deployment_simulation(
            env_overrides={"MOCK_HEALTH_FAIL": "1"},
            initial_containers=["smart-energy-monitor"]
        )
        assert rc == 1
        assert "smart-energy-monitor" in containers
        assert "ERROR: Replacement container failed Docker health check" in stdout
        assert "Initiating rollback to previous working container..." in stdout
        assert "Previous working container successfully restored" in stdout

    def test_http_health_failure_triggers_rollback(self):
        """When replacement fails HTTP health check, rollback restores previous container and exits nonzero."""
        rc, stdout, stderr, containers = run_deployment_simulation(
            env_overrides={"MOCK_FAIL_HTTP": "1"},
            initial_containers=["smart-energy-monitor"]
        )
        assert rc == 1
        assert "smart-energy-monitor" in containers
        assert "ERROR: Final local HTTP health check failed" in stdout
        assert "Initiating rollback to previous working container..." in stdout
        assert "Previous working container successfully restored" in stdout

    def test_stop_failure_aborts_without_damaging_container(self):
        """When docker stop fails, container is not damaged, BACKUP_PRESERVED=0, exits nonzero without rollback."""
        rc, stdout, stderr, containers = run_deployment_simulation(
            env_overrides={"MOCK_FAIL_STOP": "1"},
            initial_containers=["smart-energy-monitor"]
        )
        assert rc == 1
        assert "smart-energy-monitor" in containers
        assert "ERROR: Failed to stop current container for backup." in stdout
        assert "Initiating rollback" not in stdout

    def test_rename_to_newbackup_failure_restarts_container(self):
        """When rename to staged backup fails, container is restarted, exits nonzero without rollback."""
        rc, stdout, stderr, containers = run_deployment_simulation(
            env_overrides={"MOCK_FAIL_RENAME_NEWBACKUP": "1"},
            initial_containers=["smart-energy-monitor"]
        )
        assert rc == 1
        assert "smart-energy-monitor" in containers
        assert "ERROR: Failed to rename current container to staged backup." in stdout
        assert "Initiating rollback" not in stdout

    def test_remove_old_backup_failure_restores_staged_backup(self):
        """When removing old backup fails, staged newbackup is preserved and restored by rollback."""
        rc, stdout, stderr, containers = run_deployment_simulation(
            env_overrides={"MOCK_FAIL_RM_BACKUP": "1"},
            initial_containers=["smart-energy-monitor", "smart-energy-monitor-backup"]
        )
        assert rc == 1
        assert "smart-energy-monitor" in containers
        assert "ERROR: Failed to remove old backup container. Staged backup remains preserved." in stdout
        assert "Restoring previous working container from smart-energy-monitor-newbackup..." in stdout
        assert "Previous working container successfully restored" in stdout

    def test_backup_promotion_failure_restores_staged_backup(self):
        """When promotion to backup fails, staged newbackup is preserved and restored by rollback."""
        rc, stdout, stderr, containers = run_deployment_simulation(
            env_overrides={"MOCK_FAIL_PROMOTION": "1"},
            initial_containers=["smart-energy-monitor"]
        )
        assert rc == 1
        assert "smart-energy-monitor" in containers
        assert "ERROR: Failed to promote staged backup to primary backup." in stdout
        assert "Restoring previous working container from smart-energy-monitor-newbackup..." in stdout
        assert "Previous working container successfully restored" in stdout

    def test_first_deployment_without_existing_container(self):
        """First deployment on empty host without container exits cleanly without invalid restore."""
        rc, stdout, stderr, containers = run_deployment_simulation(
            env_overrides={"MOCK_FAIL_RUN": "1"},
            initial_containers=[]
        )
        assert rc == 1
        assert "No existing container found to preserve; proceeding with initial deployment." in stdout
        assert "No backup container to restore (first deployment without previous container)." in stdout
        assert "Restoring previous working container" not in stdout

    def test_rollback_failure_preserves_recovery_container(self):
        """If restored container fails health check, recovery container is preserved and exits nonzero."""
        rc, stdout, stderr, containers = run_deployment_simulation(
            env_overrides={"MOCK_FAIL_RUN": "1", "MOCK_RESTORE_HEALTH_FAIL": "1"},
            initial_containers=["smart-energy-monitor"]
        )
        assert rc == 1
        assert "smart-energy-monitor" in containers
        assert "CRITICAL: Rollback verification failed - restored container failed health check" in stdout
        assert "Recovery container preserved." in stdout
        assert "CRITICAL: Deployment failed and rollback was unsuccessful" in stdout

    def test_cleanup_failure_does_not_trigger_rollback_or_lose_recovery_container(self):
        """Failure during backup cleanup does not trigger rollback, retains healthy running container, and preserves recovery container."""
        rc, stdout, stderr, containers = run_deployment_simulation(
            env_overrides={"MOCK_FAIL_CLEANUP": "1"},
            initial_containers=["smart-energy-monitor"]
        )
        assert rc == 0
        assert "smart-energy-monitor" in containers, "Running replacement container must not be killed"
        assert "smart-energy-monitor-backup" in containers, "Recovery container whose deletion failed must remain preserved"
        assert "WARNING: Failed to remove backup container." in stdout
        assert "Initiating rollback" not in stdout, "Rollback must not be triggered during cleanup"
        assert "Deployment finalized successfully." in stdout
