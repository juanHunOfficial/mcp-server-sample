from server import mcp


# Define a simple prompt
@mcp.prompt(title="Solutions Expert")
def solutions_expert(context: str, supporting_docs: str, knowledge_base: str) -> str:
    """Generate the prompt for a Solutions Expert"""
    return f"""
        # Role
            You are a world class solutions expert, helping businesses solve complex problems quick and effectively.

        # Tasks
            - Given the following context, help the user by providing step-by-step instructions to their problems. 
            - If the user has an issue that is close to a description in our knowledge base then use that ticket_id to call the get_incident_by_id tool
              use the information that that tool provides to help the user with their issue.

        # Context
            {context}

        # Supporting Documents
            ## Documents
                {supporting_docs}

            ## Knowledge base data from ServiceNow
                {knowledge_base}

        # Notes
            - It is CRITICAL not to site any fabricated past incidents outside of the context and supporting documents you were given.
            - If there is nothing in the supporting documentation that can aid you then give the best solution that 
              you are aware of related to the context. 
            - List the steps of your solution in numerical order. 
            - **IMPORTANT** When calling the get_incident_by_id tool you MUST match the ticket_id you got from the knowledge base with the ticket_id parameter you send
              for example "KB00015" is the one you want, then pass "KB00015" as the parameter.
    """


# NOTE: These examples are for GitHub Copilot use not for use in a production level program
@mcp.prompt(title="Deployment Readiness Check")
def pre_deployment_prompt() -> str:
    """Generate a pre-deployment readiness checklist prompt for developers"""
    return """
        Use Case:
            A developer finishes a feature and asks GitHub Copilot:
                "Am I ready to deploy this?"

        Purpose:
            This prompt guides the developer through a structured readiness checklist
            before deployment. It dynamically adapts based on responses and can invoke
            external tools to fetch missing data.

        Prompt Flow:
            1. Ask clarifying questions:
                - Have all automated tests passed?
                - Is the Jira ticket linked to the PR?
                - Has the security scan been completed?
            2. Dynamically adapt follow-up questions based on answers.
            3. Optionally invoke actions to retrieve or trigger missing steps.

        Questions:
            - tests_passed (boolean, required): "Have all automated tests passed?"
            - jira_linked (boolean, required): "Is the Jira ticket linked to the PR?"
            - security_scan (boolean, required): "Has the security scan been completed?"
            - additional_notes (string, optional): "Any additional notes or blockers?"

        Dynamic Logic:
            if not tests_passed:
                ask("Would you like me to fetch the latest test results?")
            if not jira_linked:
                ask("Should I check the Jira ticket status for you?")
            if not security_scan:
                ask("Do you want me to trigger a security scan now?")

        Actions:
            - fetch_test_results: Fetch latest CI/CD test results (endpoint: /ci/tests/latest)
            - check_jira_status: Check Jira ticket status linked to PR (endpoint: /jira/status)
            - run_security_scan: Trigger or verify security scan (endpoint: /security/scan)
    """


@mcp.prompt(title="Pre-Merge Checklist")
def pre_merge_checklist() -> str:
    """Generate a pre-merge checklist prompt for developers"""
    return """
    Use Case:
        A developer asks: "Can I merge this PR?"

    Purpose:
        Guides the developer through a pre-merge checklist to ensure quality and compliance.

    Questions:
        - "Has the PR been approved by at least one reviewer?"
        - "Are all CI checks green?"
        - "Is the branch up to date with main?"
        - "Have you updated the changelog?"

    Dynamic Logic:
        if not approved:
            ask("Would you like me to suggest reviewers?")
        if not ci_green:
            ask("Should I fetch the latest CI status?")
        if not up_to_date:
            ask("Do you want me to rebase this branch?")

    Actions:
        - get_code_reviewers
        - fetch_ci_status
        - trigger_rebase
    """
