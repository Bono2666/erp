/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class SplashScreen extends Component {
    setup() {}
}

SplashScreen.template = "general.SplashScreen";
SplashScreen.props = {};

registry.category("actions").add("general_splash", SplashScreen);
