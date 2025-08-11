import hcl2
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Terraform Demo Advanced")

def parse_tf(path: str):
    with open(path, "r") as f:
        data = hcl2.load(f)

    # Collect variable names
    variables = [list(d.keys())[0] for d in data.get("variable", [])]

    # Collect provider names
    providers = [list(d.keys())[0] for d in data.get("provider", [])]

    # Collect resources as type.name
    resources = []
    for r in data.get("resource", []):
        for rtype, rbody in r.items():
            for name in rbody.keys():
                resources.append(f"{rtype}.{name}")

    # Collect outputs if present
    outputs = [list(d.keys())[0] for d in data.get("output", [])]

    return {
        "variables": variables,
        "providers": providers,
        "resources": resources,
        "outputs": outputs
    }

@mcp.tool()
def get_env(path: str) -> dict:
    """Return variables, providers, resources, and outputs from a Terraform file."""
    return parse_tf(path)

if __name__ == "__main__":
    print("Run with: mcp dev ./terraform_demo_server.py")
