from datetime import datetime
import requests

def log_crm_heartbeat():
    """Logs a heartbeat message every 5 minutes and checks GraphQL hello endpoint."""
    now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    message = f"{now} CRM is alive"

    # Optional: check GraphQL hello field
    try:
        resp = requests.post(
            "http://localhost:8000/graphql",
            json={"query": "{ hello }"},
            timeout=5
        )
        if resp.ok and "hello" in resp.json().get("data", {}):
            message += " (GraphQL responsive)"
        else:
            message += " (GraphQL failed)"
    except Exception:
        message += " (GraphQL error)"

    with open("/tmp/crm_heartbeat_log.txt", "a") as f:
        f.write(message + "\n")

from datetime import datetime
import requests

def log_crm_heartbeat():
    """Logs a heartbeat message every 5 minutes and checks GraphQL hello endpoint."""
    now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    message = f"{now} CRM is alive"

    # Optional: check GraphQL hello field
    try:
        resp = requests.post(
            "http://localhost:8000/graphql",
            json={"query": "{ hello }"},
            timeout=5
        )
        if resp.ok and "hello" in resp.json().get("data", {}):
            message += " (GraphQL responsive)"
        else:
            message += " (GraphQL failed)"
    except Exception:
        message += " (GraphQL error)"

    with open("/tmp/crm_heartbeat_log.txt", "a") as f:
        f.write(message + "\n")


def update_low_stock():
    """
    Calls GraphQL mutation to restock products with stock < 10
    and logs updates into /tmp/low_stock_updates_log.txt
    """
    now = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    log_msg = f"{now} UpdateLowStockProducts: "

    mutation = """
    mutation {
        updateLowStockProducts {
            message
            updatedProducts {
                id
                name
                stock
            }
        }
    }
    """

    try:
        resp = requests.post(
            "http://localhost:8000/graphql",
            json={"query": mutation},
            timeout=10
        )
        data = resp.json()

        if "errors" in data:
            log_msg += f"Failed with errors: {data['errors']}"
        else:
            result = data["data"]["updateLowStockProducts"]
            log_msg += result["message"]
            for p in result["updatedProducts"]:
                log_msg += f"\n   - {p['name']} → stock: {p['stock']}"

    except Exception as e:
        log_msg += f"Request error: {str(e)}"

    with open("/tmp/low_stock_updates_log.txt", "a") as f:
        f.write(log_msg + "\n")
