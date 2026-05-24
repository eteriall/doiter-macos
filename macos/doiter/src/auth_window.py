"""Login and registration window for the macOS app."""

import objc
from Foundation import NSObject, NSMakeRect
from AppKit import (
    NSBackingStoreBuffered,
    NSButton,
    NSCenterTextAlignment,
    NSColor,
    NSFont,
    NSSecureTextField,
    NSTextField,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
)

from .api_client import APIError


class AuthDelegate(NSObject):
    def init(self):
        self = objc.super(AuthDelegate, self).init()
        if self is None:
            return None
        self.window_ref = None
        return self

    def setWindowRef_(self, window_ref):
        self.window_ref = window_ref

    def login_(self, sender):
        self.window_ref.submit("login")

    def register_(self, sender):
        self.window_ref.submit("register")

    def windowWillClose_(self, notification):
        self.window_ref.closed()


class AuthWindow:
    def __init__(self, api_client, on_authenticated, on_closed=None):
        self.api_client = api_client
        self.on_authenticated = on_authenticated
        self.on_closed = on_closed
        self.is_visible = False
        self._authenticated = False
        self.delegate = AuthDelegate.alloc().init()
        self.delegate.setWindowRef_(self)

        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 360, 250),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("doiter account")
        self.window.setDelegate_(self.delegate)
        self.window.center()
        self._create_ui()

    def _create_ui(self):
        title = NSTextField.alloc().initWithFrame_(NSMakeRect(24, 196, 312, 28))
        title.setStringValue_("Sign in to doiter")
        title.setFont_(NSFont.boldSystemFontOfSize_(20))
        title.setEditable_(False)
        title.setBordered_(False)
        title.setDrawsBackground_(False)
        title.setAlignment_(NSCenterTextAlignment)
        self.window.contentView().addSubview_(title)

        self.username = NSTextField.alloc().initWithFrame_(NSMakeRect(42, 142, 276, 28))
        self.username.setPlaceholderString_("Username")
        self.window.contentView().addSubview_(self.username)

        self.password = NSSecureTextField.alloc().initWithFrame_(NSMakeRect(42, 104, 276, 28))
        self.password.setPlaceholderString_("Password")
        self.window.contentView().addSubview_(self.password)

        login_button = NSButton.alloc().initWithFrame_(NSMakeRect(42, 58, 128, 32))
        login_button.setTitle_("Login")
        login_button.setTarget_(self.delegate)
        login_button.setAction_("login:")
        self.window.contentView().addSubview_(login_button)

        register_button = NSButton.alloc().initWithFrame_(NSMakeRect(190, 58, 128, 32))
        register_button.setTitle_("Create account")
        register_button.setTarget_(self.delegate)
        register_button.setAction_("register:")
        self.window.contentView().addSubview_(register_button)

        self.status = NSTextField.alloc().initWithFrame_(NSMakeRect(24, 22, 312, 22))
        self.status.setEditable_(False)
        self.status.setBordered_(False)
        self.status.setDrawsBackground_(False)
        self.status.setTextColor_(NSColor.systemRedColor())
        self.status.setAlignment_(NSCenterTextAlignment)
        self.window.contentView().addSubview_(self.status)

    def show(self):
        self._authenticated = False
        self.is_visible = True
        self.window.makeKeyAndOrderFront_(None)
        self.window.makeFirstResponder_(self.username)

    def closed(self):
        self.is_visible = False
        if not self._authenticated and self.on_closed:
            self.on_closed()

    def submit(self, mode: str):
        username = self.username.stringValue().strip()
        password = self.password.stringValue()
        if not username or not password:
            self.status.setStringValue_("Enter username and password")
            return

        try:
            if mode == "register":
                self.api_client.register(username, password)
            else:
                self.api_client.login(username, password)
        except APIError as exc:
            self.status.setStringValue_(str(exc)[:120])
            return

        self.status.setStringValue_("")
        self._authenticated = True
        self.is_visible = False
        self.window.orderOut_(None)
        self.on_authenticated()
