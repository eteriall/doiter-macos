"""Settings window for API server configuration."""

import objc
from Foundation import NSObject, NSMakeRect
from AppKit import (
    NSBackingStoreBuffered,
    NSButton,
    NSCenterTextAlignment,
    NSTextField,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
)


class SettingsDelegate(NSObject):
    def init(self):
        self = objc.super(SettingsDelegate, self).init()
        if self is None:
            return None
        self.window_ref = None
        return self

    def setWindowRef_(self, window_ref):
        self.window_ref = window_ref

    def save_(self, sender):
        self.window_ref.save()


class SettingsWindow:
    def __init__(self, config_store):
        self.config_store = config_store
        self.delegate = SettingsDelegate.alloc().init()
        self.delegate.setWindowRef_(self)
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 420, 170),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("doiter settings")
        self.window.center()
        self._create_ui()

    def _create_ui(self):
        label = NSTextField.alloc().initWithFrame_(NSMakeRect(28, 112, 364, 22))
        label.setStringValue_("Server API URL")
        label.setEditable_(False)
        label.setBordered_(False)
        label.setDrawsBackground_(False)
        self.window.contentView().addSubview_(label)

        self.url_field = NSTextField.alloc().initWithFrame_(NSMakeRect(28, 78, 364, 28))
        self.window.contentView().addSubview_(self.url_field)

        button = NSButton.alloc().initWithFrame_(NSMakeRect(150, 34, 120, 32))
        button.setTitle_("Save")
        button.setTarget_(self.delegate)
        button.setAction_("save:")
        self.window.contentView().addSubview_(button)

        self.status = NSTextField.alloc().initWithFrame_(NSMakeRect(28, 10, 364, 18))
        self.status.setEditable_(False)
        self.status.setBordered_(False)
        self.status.setDrawsBackground_(False)
        self.status.setAlignment_(NSCenterTextAlignment)
        self.window.contentView().addSubview_(self.status)

    def show(self):
        self.url_field.setStringValue_(self.config_store.get_api_base_url())
        self.status.setStringValue_("")
        self.window.makeKeyAndOrderFront_(None)
        self.window.makeFirstResponder_(self.url_field)

    def save(self):
        value = self.url_field.stringValue().strip()
        if not value:
            self.status.setStringValue_("Server URL is required")
            return
        self.config_store.set_api_base_url(value)
        self.status.setStringValue_("Saved")
