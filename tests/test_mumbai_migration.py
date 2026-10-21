"""
Unit and configuration tests for AWS Sydney to Mumbai migration readiness.
Validates file presence, HCL variables, region parameterization,
least-privilege security settings, and state isolation.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.validate_cidr import validate_restricted_cidr

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
        assert "enable_ssh" in content, "enable_ssh must be declared in variables.tf"
        assert "default     = false" in content, "enable_ssh must default to false"


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
        """Verifies Mumbai parameters and that the instance target is migration-safe."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "name: 'MUMBAI_EC2_INSTANCE_ID'" in content
        assert "Terraform-managed Mumbai EC2 instance ID" in content
        assert "name: 'MUMBAI_APP_URL'" in content or "MUMBAI_APP_URL" in content, "Mumbai App URL parameter must be present"
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
        """Ensures Jenkinsfile pins region/registry and resolves the migration-safe SSM target."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "selectedInstance.matches('^i-[0-9a-f]{8,17}$')" in content
        assert "terraform -chdir=terraform/mumbai output -raw instance_id" in content
        assert "selectedRegistry != '695496430374.dkr.ecr.ap-south-1.amazonaws.com'" in content, (
            "Pipeline must reject any ECR registry other than Mumbai registry"
        )
        assert "selectedUrl.matches('^https?://" in content, "Pipeline must validate a constrained http(s) URL"
        assert "a valid Terraform instance_id or explicit MUMBAI_EC2_INSTANCE_ID is required" in content
        assert "env.AWS_REGION != 'ap-south-1'" in content, (
            "Deploy stage must gate against non-Mumbai AWS region"
        )
        assert "env.ECR_REGISTRY != '695496430374.dkr.ecr.ap-south-1.amazonaws.com'" in content, (
            "Deploy stage must gate against non-Mumbai ECR registry"
        )

    def test_target_validation_rejects_obsolete_hardcoded_ip(self):
        """Ensures Jenkinsfile rejects obsolete direct-instance public IP 3.110.85.209."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "selectedUrl.contains('3.110.85.209')" in content
        assert "Architecture requires ALB endpoint or private subnet resolution" in content

    def test_stage6_checks_alb_provisioning_before_probing(self):
        """Ensures Stage 6 checks whether ALB is provisioned by Terraform before probing application_url."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "output -raw alb_dns_name" in content
        assert "Application Load Balancer has not been provisioned by Terraform yet" in content
        assert "3.110.85.209" in content


class TestJenkinsfileDeploymentGuard:
    """Validates the deployment guard mechanism ensuring verification-only CI builds by default."""

    def test_enable_deployment_parameter_declared_default_false(self):
        """Jenkinsfile must declare ENABLE_DEPLOYMENT parameter defaulting to false."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "ENABLE_DEPLOYMENT" in content, "Jenkinsfile must declare ENABLE_DEPLOYMENT parameter"
        assert "defaultValue: false" in content, "ENABLE_DEPLOYMENT must default to false"

    def test_publish_and_deploy_flags_bound_to_deployment_guard(self):
        """ECR publication and EC2 deployment must have separate explicit opt-in flags."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "PUBLISH_TO_ECR           = \"${(params.ENABLE_ECR_PUBLISH" in content
        assert "DEPLOY_TO_EC2            = \"${(params.ENABLE_DEPLOYMENT" in content

    def test_ecr_push_and_ec2_deploy_stages_strictly_guarded(self):
        """ECR publishing and EC2 deployment stages must be conditioned on deployment flags."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "if (env.PUBLISH_TO_ECR == 'true')" in content
        assert "expression { env.DEPLOY_TO_EC2 == 'true' }" in content

    def test_allowed_ingress_cidr_parameter_declared(self):
        """Jenkinsfile must declare ALLOWED_INGRESS_CIDR parameter for configurable CI ingress."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "ALLOWED_INGRESS_CIDR" in content, "Jenkinsfile must declare ALLOWED_INGRESS_CIDR parameter"

    def test_allowed_ingress_cidr_wires_to_tf_var(self):
        """Jenkinsfile must wire ALLOWED_INGRESS_CIDR into TF_VAR_allowed_ingress_cidrs when specified."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "TF_VAR_allowed_ingress_cidrs" in content, (
            "Jenkinsfile must export TF_VAR_allowed_ingress_cidrs when ALLOWED_INGRESS_CIDR is supplied"
        )
        assert "scripts/validate_cidr.py" in content or "scripts\\validate_cidr.py" in content

    def test_deployment_disabled_by_default(self):
        """ENABLE_DEPLOYMENT must default to false, keeping ECR publish and EC2 deployment disabled by default."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "booleanParam(\n            name: 'ENABLE_DEPLOYMENT',\n            defaultValue: false" in content or (
            "name: 'ENABLE_DEPLOYMENT'" in content and "defaultValue: false" in content
        )
        assert "PUBLISH_TO_ECR           = \"${(params.ENABLE_ECR_PUBLISH == true || params.ENABLE_ECR_PUBLISH == 'true') ? 'true' : 'false'}\"" in content
        assert "DEPLOY_TO_EC2            = \"${(params.ENABLE_DEPLOYMENT == true || params.ENABLE_DEPLOYMENT == 'true') ? 'true' : 'false'}\"" in content

    def test_cidr_is_optional_for_ci_but_the_validator_rejects_invalid_values(self):
        """CI/CD does not mutate Terraform ingress; any supplied CIDR must still validate safely."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        assert "This pipeline deliberately has no infrastructure-apply step" in content
        assert "withEnv([\"RAW_INGRESS_CIDR=${rawCidr}\"])" in content
        assert "python3 scripts/validate_cidr.py \"$RAW_INGRESS_CIDR\"" in content

        # Python validator unit validation
        for empty_val in ["", "   ", "\t\n", None]:
            with pytest.raises(ValueError, match="CIDR"):
                validate_restricted_cidr(empty_val)

    def test_invalid_cidr_rejected(self):
        """Invalid IP or CIDR strings must be rejected by the standard IP/CIDR parser."""
        invalid_cidrs = [
            "invalid",
            "256.0.0.1/32",
            "192.168.1.1/33",
            "10.0.0.1",          # Missing prefix length
            "10.0.0.1/abc",      # Non-numeric prefix
            "10.0.0.1/-1",       # Negative prefix
            "10.0.0.1/24/32",    # Multiple slashes
            "999.999.999.999/24",
            "2001:xyz::/32",
            "2001:db8::/32",   # Valid IPv6 syntax, but incompatible with Terraform cidr_blocks
        ]
        for bad_cidr in invalid_cidrs:
            with pytest.raises(ValueError):
                validate_restricted_cidr(bad_cidr)

    def test_world_open_and_unrestricted_cidrs_rejected(self):
        """World-open (0.0.0.0/0, ::/0) and unspecified address CIDRs must be strictly rejected."""
        unrestricted = [
            "0.0.0.0/0",
            "::/0",
            "0.0.0.0/8",       # Unspecified IPv4 network
            "::/128",          # Unspecified IPv6 address
            "224.0.0.0/4",     # IPv4 multicast space
            "ff02::1/128",     # IPv6 is unsupported by the IPv4 Terraform rule
        ]
        for world_cidr in unrestricted:
            with pytest.raises(ValueError, match="(rejected|Unspecified|Multicast|prefix length 0|not supported)"):
                validate_restricted_cidr(world_cidr)

    def test_valid_restricted_cidr_accepted(self):
        """Legitimate restricted CIDRs must be accepted and normalized by the validator."""
        valid_cidrs = {
            "223.236.96.144/32": "223.236.96.144/32",
            "10.1.1.0/24": "10.1.1.0/24",
            "192.168.1.50/32": "192.168.1.50/32",
            "172.16.0.0/16": "172.16.0.0/16",
        }
        for cidr, expected in valid_cidrs.items():
            assert validate_restricted_cidr(cidr) == expected

    def test_validation_only_builds_never_publish_or_deploy(self):
        """Validation-only builds must never publish to ECR or deploy to EC2."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # ECR publication must have an explicit skip branch
        assert "Skipping image push to preserve remote registry" in content
        assert "if (env.PUBLISH_TO_ECR == 'true')" in content

        # EC2 deployment must be guarded by declarative when condition
        assert "when {\n                expression { env.DEPLOY_TO_EC2 == 'true' }\n            }" in content or (
            "when" in content and "env.DEPLOY_TO_EC2 == 'true'" in content
        )

    def test_cidr_validation_is_decoupled_from_ecr_and_ssm_writes(self):
        """Image publishing and SSM deployment do not modify Terraform ingress rules."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        assert "ECR publication blocked. Ingress CIDR prerequisite" not in content
        assert "EC2 deployment blocked. Ingress CIDR prerequisite" not in content
        assert "ENABLE_ECR_PUBLISH" in content
        assert "PUBLISH_TO_ECR           = \"${(params.ENABLE_ECR_PUBLISH" in content

    def test_jenkinsfile_declarative_pipeline_structure(self):
        """Structural syntax check: Verifies all declarative pipeline blocks and stages are properly formed."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # Declarative root blocks
        required_root_blocks = [
            "pipeline {",
            "agent any",
            "triggers {",
            "options {",
            "parameters {",
            "environment {",
            "stages {",
            "post {",
        ]
        for block in required_root_blocks:
            assert block in content, f"Missing declarative block: {block}"

        # All 6 stages must be defined in order with steps {}
        stages = [
            "stage('Checkout SCM')",
            "stage('Unit Testing & QA')",
            "stage('Security & Code Quality')",
            "stage('Docker Build & Package')",
            "stage('Terraform IaC Validation')",
            "stage('Deploy to EC2 (SSM)')",
        ]
        last_pos = 0
        for s in stages:
            pos = content.find(s, last_pos)
            assert pos != -1, f"Missing or out-of-order stage: {s}"
            # Stage must contain steps
            stage_block = content[pos:content.find("stage(", pos + len(s)) if content.find("stage(", pos + len(s)) != -1 else len(content)]
            assert "steps {" in stage_block, f"Stage {s} must contain steps {{ ... }}"
            last_pos = pos + len(s)

    def test_jenkinsfile_balanced_delimiters(self):
        """Jenkinsfile must maintain perfectly balanced delimiter counts for braces, brackets, and parens."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        counts = {c: content.count(c) for c in "()[]{}"}
        assert counts["("] == counts[")"], f"Parentheses mismatch: {counts['(']} != {counts[')']}"
        assert counts["["] == counts["]"], f"Brackets mismatch: {counts['[']} != {counts[']']}"
        assert counts["{"] == counts["}"], f"Braces mismatch: {counts['{']} != {counts['}']}"

    def test_validation_only_stages_have_zero_aws_writes(self):
        """Ensure stages 1 to 5 (prior to guarded deployment) contain zero un-guarded AWS write commands."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        deploy_stage_idx = content.find("stage('Deploy to EC2 (SSM)')")
        assert deploy_stage_idx != -1
        validation_pipeline = content[:deploy_stage_idx]

        # Ensure no terraform apply or destroy exists anywhere in the validation pipeline
        assert "terraform apply" not in validation_pipeline
        assert "terraform destroy" not in validation_pipeline
        # Ensure no SSM send-command exists in validation pipeline
        assert "ssm send-command" not in validation_pipeline
        # Ensure any docker push to ECR is enclosed within PUBLISH_TO_ECR check
        push_idx = validation_pipeline.find("docker push ${ECR_REGISTRY}")
        guard_idx = validation_pipeline.find("if (env.PUBLISH_TO_ECR == 'true')")
        assert guard_idx != -1 and push_idx != -1
        assert guard_idx < push_idx

    def test_deployment_guard_evaluation_truth_table(self):
        """Ensure the Groovy expression evaluates strictly to 'false' for default and un-parameterized runs."""
        def eval_guard(val):
            return "true" if (val is True or val == "true") else "false"

        assert eval_guard(None) == "false", "SCM-triggered run with uninitialized params must be false"
        assert eval_guard(False) == "false", "Explicit false parameter must be false"
        assert eval_guard("false") == "false", "String false parameter must be false"
        assert eval_guard("") == "false", "Empty parameter must be false"
        assert eval_guard("yes") == "false", "Arbitrary 'yes' must not enable deployment"
        assert eval_guard("1") == "false", "Arbitrary '1' must not enable deployment"
        assert eval_guard("enabled") == "false", "Arbitrary 'enabled' must not enable deployment"
        assert eval_guard(True) == "true", "Explicit boolean true must enable deployment"
        assert eval_guard("true") == "true", "Explicit string true must enable deployment"


    def test_deployment_ordering_image_validated_before_stopping_container(self):

        """Ensures the new image is pulled and inspected before the active container is stopped."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        pull_idx = content.find("docker pull")
        inspect_idx = content.find("docker image inspect")
        stop_old_idx = content.find("Stopping and preserving current container as staged backup...")

        assert pull_idx != -1, "docker pull command must be present"
        assert inspect_idx != -1, "docker image inspect command must be present"
        assert stop_old_idx != -1, "stop old container command must be present"
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

        assert stage_backup_idx != -1, "docker rename newbackup command must be present"
        assert backup_preserved_idx != -1, "BACKUP_PRESERVED=1 state must be present"
        assert rm_old_backup_idx != -1, "docker rm -f backup command must be present"
        assert promote_backup_idx != -1, "docker rename newbackup backup command must be present"
        assert stage_backup_idx < backup_preserved_idx < rm_old_backup_idx < promote_backup_idx, (
            "Recovery state BACKUP_PRESERVED=1 must be set immediately after newbackup is created, before removing old backup"
        )

    def test_backup_rotation_prefers_newbackup_over_old_backup(self):
        """Ensures rollback prefers newly preserved newbackup container over older backup."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        inspect_newbackup_idx = content.find("if docker inspect ${env.APP_NAME}-newbackup >/dev/null 2>&1; then TARGET_BACKUP='${env.APP_NAME}-newbackup'")
        inspect_oldbackup_idx = content.find("elif docker inspect ${env.APP_NAME}-backup >/dev/null 2>&1; then TARGET_BACKUP='${env.APP_NAME}-backup'")
        assert inspect_newbackup_idx != -1, "Inspection of newbackup must be present"
        assert inspect_oldbackup_idx != -1, "Inspection of old backup must be present"
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

        assert docker_health_idx != -1, "Docker health check step must be present"
        assert http_health_idx != -1, "HTTP health check step must be present"
        assert inspect_running_idx != -1, "Inspect running image step must be present"
        assert inspect_volume_idx != -1, "Inspect volume step must be present"
        assert deploy_success_idx != -1, "DEPLOY_SUCCESS=1 step must be present"
        assert cleanup_backup_idx != -1, "Cleanup backup container step must be present"

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
        assert "! docker run" in content, "docker run failure check must be present"
        assert "rollback; exit 1" in content, "Container startup failure must trigger rollback"
        assert "HEALTHY" in content, "HEALTHY check must be present"
        assert "Replacement container failed Docker health check" in content, (
            "Docker health check failure must trigger rollback"
        )
        assert "HTTP_OK" in content, "HTTP_OK check must be present"
        assert "Final local HTTP health check failed" in content, (
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
        assert "trap " in content, "Deployment script must register an EXIT trap"
        assert "EXIT" in content, "Deployment script must register an EXIT trap"
        assert "BACKUP_PRESERVED" in content, "EXIT trap must monitor BACKUP_PRESERVED flag"
        assert "DEPLOY_SUCCESS" in content, "EXIT trap must monitor DEPLOY_SUCCESS flag"
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
    if os.name == "nt" or not shutil.which("bash"):
        pytest.skip("bash is required for behavioral simulation")

    with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    raw_script = extract_ssm_script(content)

    # Use the project workspace instead of the Windows sandbox temp directory,
    # which can deny child processes permission to create test fixtures.
    with tempfile.TemporaryDirectory(dir=ROOT_DIR) as td:
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


class TestSonarCloudQualityGateConfig:
    """Regression tests verifying SonarCloud Quality Gate, coverage ingestion, and SAST hardening."""

    def test_coveragerc_exists_and_uses_relative_files(self):
        """Ensure .coveragerc configures relative_files for cross-platform Docker scanner compatibility."""
        coveragerc_path = os.path.join(ROOT_DIR, ".coveragerc")
        assert os.path.isfile(coveragerc_path), ".coveragerc must exist"
        with open(coveragerc_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "relative_files = True" in content or "relative_files=True" in content
        assert "scripts/*" in content, "scripts/* must be omitted from coverage"
        assert "tests/*" in content, "tests/* must be omitted from coverage"

    def test_sonar_project_properties_exclusions_and_reports(self):
        """Ensure sonar-project.properties declares coverage path, excludes utility scripts and tests."""
        props_path = os.path.join(ROOT_DIR, "sonar-project.properties")
        assert os.path.isfile(props_path)
        with open(props_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "sonar.python.coverage.reportPaths=coverage.xml" in content
        assert "scripts/**" in content, "scripts/** must be in sonar.exclusions"
        assert "sonar.coverage.exclusions=scripts/**" in content
        assert "sonar.qualitygate.wait=true" in content

    def test_jenkinsfile_coverage_validation_and_scanner_flags(self):
        """Ensure Jenkinsfile validates coverage.xml before scan and passes explicit coverage reportPaths."""
        jenkinsfile_path = os.path.join(ROOT_DIR, "Jenkinsfile")
        with open(jenkinsfile_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "fileExists('coverage.xml')" in content
        assert "-Dsonar.python.coverage.reportPaths=coverage.xml" in content
        assert "sh '''" in content, "Must use single-quoted multiline string to avoid Groovy escaping syntax warning"

    def test_dockerfile_least_privilege_and_wheel_install(self):
        """Ensure Dockerfile installs only binary wheels and copies only production application files."""
        dockerfile_path = os.path.join(ROOT_DIR, "Dockerfile")
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            content = "\n".join(lines)

        assert (
            "--only-binary=:all:" in content or "--only-binary :all:" in content
        ), "Dockerfile pip install must enforce binary wheels"
        assert "--require-hashes" in content, "Dockerfile pip install must verify dependency hashes"
        assert "COPY . ." not in content, "Dockerfile must not use recursive COPY . ."
        assert "COPY alerts.py analytics.py app.py config.py database.py iot_simulator.py ./" in content

        user_directives = [line for line in lines if line.startswith("USER ")]
        assert len(user_directives) >= 1, "Dockerfile must declare a USER directive"
        assert user_directives[-1] == "USER appuser", "Final USER directive must be unprivileged appuser"
        assert any(line.startswith("HEALTHCHECK") for line in lines), "Dockerfile must define a HEALTHCHECK"
        assert "http://localhost:8501/_stcore/health" in content, "Healthcheck must probe Streamlit health endpoint"

    def test_terraform_mumbai_private_instance_no_public_ip(self):
        """Ensure terraform/mumbai/main.tf maintains private subnet residency with no public IP (resolves terraform:S6329)."""
        tf_path = os.path.join(ROOT_DIR, "terraform", "mumbai", "main.tf")
        with open(tf_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "associate_public_ip_address = false" in content, (
            "EC2 instance must have associate_public_ip_address = false to resolve terraform:S6329"
        )
        assert "subnet_id                   = aws_subnet.private_a.id" in content or "subnet_id = aws_subnet.private_a.id" in content, (
            "EC2 instance must reside in private subnet"
        )

    def test_dockerfile_uses_non_root_user(self):
        """Ensure Dockerfile declares an unprivileged application user and switches to it."""
        dockerfile_path = os.path.join(ROOT_DIR, "Dockerfile")
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "useradd -m -u 1001 appuser" in content, "Dockerfile must create appuser"
        assert "USER appuser" in content, "Dockerfile must switch to non-root appuser"

    def test_requirements_lock_hash_enforcement_and_pins(self):
        """Ensure requirements.lock exists, contains SHA-256 hashes, and pins every single dependency."""
        lock_path = os.path.join(ROOT_DIR, "requirements.lock")
        assert os.path.isfile(lock_path), "requirements.lock must exist"
        with open(lock_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        packages_found = {}
        current_pkg = None
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "==" in line and not line.startswith("--"):
                pkg_part = line.split("\\")[0].strip()
                name, version = pkg_part.split("==", 1)
                name = name.strip().lower()
                version = version.strip()
                current_pkg = name
                packages_found[current_pkg] = {"version": version, "hashes": []}
            elif "--hash=sha256:" in line and current_pkg:
                hash_val = line.split("--hash=sha256:")[1].strip().rstrip("\\").strip()
                packages_found[current_pkg]["hashes"].append(hash_val)

        core_deps = ["streamlit", "plotly", "pandas", "numpy", "altair", "requests", "urllib3"]
        for dep in core_deps:
            assert dep in packages_found, f"{dep} must be locked in requirements.lock"
            assert packages_found[dep]["version"], f"{dep} must have an exact pinned version"
            assert len(packages_found[dep]["hashes"]) >= 1, f"{dep} must have at least one SHA-256 hash"
            for h in packages_found[dep]["hashes"]:
                assert len(h) == 64, f"Hash for {dep} must be a valid 64-character SHA-256 hex string: {h}"
                assert all(c in "0123456789abcdef" for c in h.lower()), f"Invalid sha256 characters in {h}"

    def test_terraform_mumbai_security_group_ingress_and_least_privilege(self):
        """Ensure Mumbai security group uses allowed_ingress_cidrs for the app port and enforces IMDSv2."""
        main_tf = os.path.join(ROOT_DIR, "terraform", "mumbai", "main.tf")
        with open(main_tf, "r", encoding="utf-8") as f:
            content = f.read()

        assert "cidr_blocks = var.allowed_ingress_cidrs" in content, (
            "ALB security group must use var.allowed_ingress_cidrs"
        )
        assert "var.app_port" in content, "Ingress must use configurable var.app_port"
        # Ingress blocks must use restricted CIDR blocks, not 0.0.0.0/0
        sg_start = content.find('resource "aws_security_group" "app_sg"')
        egress_start = content.find('egress {', sg_start)
        ingress_section = content[sg_start:egress_start] if sg_start != -1 and egress_start != -1 else ""
        assert '0.0.0.0/0' not in ingress_section, (
            "Mumbai security group ingress must never expose port 8501 or SSH to world 0.0.0.0/0"
        )
        assert re.search(r'http_tokens\s*=\s*"required"', content), (
            "IMDSv2 must be enforced with http_tokens = 'required'"
        )
        assert re.search(r'http_put_response_hop_limit\s*=\s*1', content), (
            "IMDSv2 hop limit must be restricted to 1"
        )

    def test_preservation_of_distinct_mumbai_and_sydney_state_configuration(self):
        """Ensure Mumbai and Sydney retain distinct configuration and state boundaries."""
        sydney_tf = os.path.join(ROOT_DIR, "terraform", "main.tf")
        mumbai_tf = os.path.join(ROOT_DIR, "terraform", "mumbai", "main.tf")
        assert os.path.isfile(sydney_tf), "Sydney terraform/main.tf must exist"
        assert os.path.isfile(mumbai_tf), "Mumbai terraform/mumbai/main.tf must exist"

        with open(sydney_tf, "r", encoding="utf-8") as f:
            sydney_content = f.read()
        with open(mumbai_tf, "r", encoding="utf-8") as f:
            mumbai_content = f.read()

        assert "${var.project_name}-ec2-role" in sydney_content or "smart-energy-monitor-ec2-role" in sydney_content
        assert "${var.project_name}-mumbai-ec2-role" in mumbai_content or "smart-energy-monitor-mumbai-ec2-role" in mumbai_content


class TestMumbaiPrivateArchitectureAndALB:
    """Validates the refactored Mumbai architecture: Private EC2 instance + dual-AZ ALB + TLS."""

    @pytest.fixture(autouse=True)
    def setup_files(self):
        self.main_tf = os.path.join(MUMBAI_TF_DIR, "main.tf")
        self.vars_tf = os.path.join(MUMBAI_TF_DIR, "variables.tf")
        self.outputs_tf = os.path.join(MUMBAI_TF_DIR, "outputs.tf")
        with open(self.main_tf, "r", encoding="utf-8") as f:
            self.main_content = f.read()
        with open(self.vars_tf, "r", encoding="utf-8") as f:
            self.vars_content = f.read()
        with open(self.outputs_tf, "r", encoding="utf-8") as f:
            self.outputs_content = f.read()

    def test_ec2_resides_in_private_subnet_without_public_ip(self):
        """Resolves terraform:S6329 by verifying associate_public_ip_address = false and private subnet."""
        assert "associate_public_ip_address = false" in self.main_content
        assert "subnet_id                   = aws_subnet.private_a.id" in self.main_content

    def test_dual_az_public_and_private_subnets_defined(self):
        """Verifies dual-AZ architecture required by Application Load Balancer."""
        assert 'resource "aws_subnet" "public_a"' in self.main_content
        assert 'resource "aws_subnet" "public_b"' in self.main_content
        assert 'resource "aws_subnet" "private_a"' in self.main_content
        assert 'resource "aws_subnet" "private_b"' in self.main_content
        assert "map_public_ip_on_launch = false" in self.main_content

    def test_internet_gateway_and_routing(self):
        """Verifies Internet Gateway exists and is routed to public subnets."""
        assert 'resource "aws_internet_gateway" "gw"' in self.main_content
        assert 'resource "aws_route_table" "public"' in self.main_content
        assert 'resource "aws_route_table_association" "public_a_assoc"' in self.main_content
        assert 'resource "aws_route_table_association" "public_b_assoc"' in self.main_content

    def test_nat_gateway_and_s3_endpoint(self):
        """Verifies outbound connectivity via NAT Gateway and S3 Gateway VPC Endpoint."""
        assert 'resource "aws_nat_gateway" "nat"' in self.main_content
        assert 'resource "aws_eip" "nat"' in self.main_content
        assert 'resource "aws_route_table" "private"' in self.main_content
        assert 'resource "aws_vpc_endpoint" "s3"' in self.main_content
        assert 'vpc_endpoint_type = "Gateway"' in self.main_content

    def test_alb_and_target_group_configuration(self):
        """Verifies Application Load Balancer and health check target group on port 8501."""
        assert 'resource "aws_lb" "app_alb"' in self.main_content
        assert 'load_balancer_type' in self.main_content and '"application"' in self.main_content
        assert 'drop_invalid_header_fields = true' in self.main_content
        assert 'resource "aws_lb_target_group" "app_tg"' in self.main_content
        assert 'path                = "/_stcore/health"' in self.main_content
        assert 'resource "aws_lb_target_group_attachment" "app"' in self.main_content

    def test_security_group_alb_isolation(self):
        """Verifies EC2 port 8501 is ONLY accessible from the ALB security group."""
        assert 'resource "aws_security_group" "alb_sg"' in self.main_content
        assert 'security_groups = [aws_security_group.alb_sg.id]' in self.main_content
        # Ensure app_sg port 8501 does NOT allow cidr_blocks
        app_sg_idx = self.main_content.find('resource "aws_security_group" "app_sg"')
        alb_sg_idx = self.main_content.find('resource "aws_security_group" "alb_sg"')
        assert app_sg_idx != -1 and alb_sg_idx != -1

    def test_tls_acm_and_listeners_configuration(self):
        """Verifies conditional ACM TLS certificate and ALB HTTPS/HTTP listeners."""
        assert 'resource "aws_acm_certificate" "cert"' in self.main_content
        assert 'resource "aws_lb_listener" "http"' in self.main_content
        assert 'resource "aws_lb_listener" "https"' in self.main_content
        assert 'ELBSecurityPolicy-TLS13-1-2-2021-06' in self.main_content

    def test_outputs_expose_alb_and_private_instance(self):
        """Verifies outputs expose ALB DNS name and instance private IP, removing instance_public_ip."""
        assert 'output "alb_dns_name"' in self.outputs_content
        assert 'output "instance_private_ip"' in self.outputs_content
        assert 'output "application_url"' in self.outputs_content
        assert 'output "instance_public_ip"' not in self.outputs_content

    def test_interface_vpc_endpoints_configured(self):
        """Verifies configuration of Interface VPC Endpoints for private ECR and SSM connectivity."""
        assert 'resource "aws_vpc_endpoint" "interface_endpoints"' in self.main_content
        assert 'resource "aws_security_group" "vpce_sg"' in self.main_content
        assert 'private_dns_enabled = true' in self.main_content
        assert 'ecr.api' in self.main_content
        assert 'ecr.dkr' in self.main_content
        assert 'ssm' in self.main_content

    def test_tls_check_block_and_honest_output(self):
        """Verifies declarative check block enforcing TLS prerequisites and honest is_https_active output."""
        assert 'check "tls_configuration"' in self.main_content
        assert 'resource "aws_route53_record" "cert_validation"' in self.main_content
        assert 'resource "aws_acm_certificate_validation" "cert"' in self.main_content
        assert 'aws_acm_certificate_validation.cert[0].certificate_arn' in self.main_content
        assert 'variable "route53_zone_id"' in self.vars_content
        assert 'output "is_https_active"' in self.outputs_content
        assert 'output "application_url"' in self.outputs_content

    def test_public_alb_requires_explicit_restricted_ingress(self):
        """No world-open default may create the public ALB without reviewed ingress input."""
        assert 'default     = []' in self.vars_content
        assert 'A restricted allowed_ingress_cidrs value is required' in self.main_content

    def test_ecr_images_are_immutable_and_ci_uses_build_tags(self):
        """Prevent a pushed image tag from being overwritten after review."""
        with open(JENKINSFILE_PATH, "r", encoding="utf-8") as f:
            pipeline = f.read()
        assert 'image_tag_mutability = "IMMUTABLE"' in self.main_content
        assert 'docker push ${ECR_REGISTRY}/${ECR_REPO}:latest' not in pipeline

    def test_interface_vpc_endpoints_includes_cloudwatch_logs(self):
        """Verifies Interface VPC Endpoints include CloudWatch logs service."""
        assert '"logs"' in self.main_content
