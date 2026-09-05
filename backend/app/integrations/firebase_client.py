def dispatch_push_notification(token: str, title: str, body: str):
    # Safe mock / wrapper for FCM send
    print(f"[FCM Push] To: {token[:10]}... | {title}: {body}")
    return True
