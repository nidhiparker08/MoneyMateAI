function confirmAction(message, title = "Confirm") {

    // Currently a thin wrapper over window.confirm to centralize confirmation calls.
    // Can be replaced with a custom modal in future without changing call sites.
    return window.confirm(message);

}
