/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, useRef, onMounted } from "@odoo/owl";

const D3_CDN = "https://d3js.org/d3.v7.min.js";
const FLEXTREE_CDN = "https://cdn.jsdelivr.net/npm/d3-flextree@2.1.2/build/d3-flextree.min.js";
const ORG_CHART_CDN = "https://cdn.jsdelivr.net/npm/d3-org-chart@2.6.0/build/d3-org-chart.min.js";

export class OrgStructure extends Component {
    setup() {
        this.orm = useService("orm");
        this.containerRef = useRef("treeContainer");
        this.state = useState({ loaded: false, error: null });
        onWillStart(async () => {
            await this.loadScripts();
            await this.loadData();
        });
        onMounted(() => {
            setTimeout(() => this.renderTree(), 300);
        });
    }

    async loadScripts() {
        // Load D3 first (required by d3-org-chart)
        if (typeof d3 === "undefined") {
            await new Promise((resolve, reject) => {
                const s = document.createElement("script");
                s.src = D3_CDN;
                s.onload = () => resolve();
                s.onerror = () => reject(new Error("Failed to load D3.js from CDN"));
                document.head.appendChild(s);
            });
        }

        // Load d3-flextree (required by d3-org-chart for layout)
        if (typeof d3 !== "undefined" && typeof d3.flextree === "undefined") {
            await new Promise((resolve, reject) => {
                const s = document.createElement("script");
                s.src = FLEXTREE_CDN;
                s.onload = () => resolve();
                s.onerror = () => reject(new Error("Failed to load d3-flextree from CDN"));
                document.head.appendChild(s);
            });
        }

        // Load d3-org-chart
        if (typeof d3 !== "undefined" && typeof d3.OrgChart === "undefined") {
            await new Promise((resolve, reject) => {
                const s = document.createElement("script");
                s.src = ORG_CHART_CDN;
                s.onload = () => resolve();
                s.onerror = () => reject(new Error("Failed to load d3-org-chart from CDN"));
                document.head.appendChild(s);
            });
        }
    }

    async loadData() {
        try {
            const [positions, employees] = await Promise.all([
                this.orm.searchRead("hcm.position", [["active", "=", true]],
                    ["id", "name", "parent_id", "department_id", "employee_count", "position_id"]),
                this.orm.searchRead("hcm.employee", [["status", "=", "active"]],
                    ["id", "name", "employee_id", "position_id"]),
            ]);

            // Map employees by position
            const empByPos = {};
            employees.forEach(e => {
                const pid = e.position_id ? e.position_id[0] : null;
                if (pid) {
                    if (!empByPos[pid]) empByPos[pid] = [];
                    empByPos[pid].push(e);
                }
            });

            // Build FLAT array for d3-org-chart (id + parentId format)
            const flatData = positions.map(p => ({
                id: String(p.id),
                parentId: p.parent_id ? String(p.parent_id[0]) : "",
                name: p.name,
                position_id: p.position_id,
                department: p.department_id ? p.department_id[1] : "-",
                employee_count: p.employee_count || 0,
                employees: empByPos[p.id] || [],
            }));

            // Check if we need a virtual root (multiple roots or orphaned nodes)
            const hasRoot = flatData.some(d => !d.parentId);
            const rootCount = flatData.filter(d => !d.parentId).length;

            if (rootCount === 0 && flatData.length > 0) {
                // No root at all — make the first one root
                flatData[0].parentId = "";
            } else if (rootCount > 1) {
                // Multiple roots — create a virtual root
                const virtualId = "virtual-root";
                flatData.forEach(d => {
                    if (!d.parentId) d.parentId = virtualId;
                });
                flatData.push({
                    id: virtualId,
                    parentId: "",
                    name: "Organization",
                    position_id: "",
                    department: "",
                    employee_count: flatData.reduce((s, d) => s + (d.employee_count || 0), 0),
                    employees: [],
                });
            }

            this.flatData = flatData;
            this.state.loaded = true;
        } catch (e) {
            this.state.error = e.message;
        }
    }

    renderTree() {
        if (!this.state.loaded || !this.flatData?.length) return;
        if (typeof d3 === "undefined" || typeof d3.OrgChart === "undefined") {
            this.state.error = "d3-org-chart library not loaded";
            return;
        }

        const el = this.containerRef.el;
        if (!el) return;
        el.innerHTML = "";

        try {
            new d3.OrgChart()
                .container(el)
                .data(this.flatData)
                .nodeWidth(() => 240)
                .nodeHeight(() => 130)
                .childrenMargin(() => 60)
                .compactMarginBetween(() => 30)
                .compactMarginPair(() => 80)
                .siblingsMargin(() => 20)
                .nodeContent((d) => {
                    const node = d.data;
                    const empCount = node.employee_count || 0;
                    const dept = node.department || "-";
                    const empNames = (node.employees || [])
                        .map(e => e.name)
                        .slice(0, 4)
                        .join(", ");
                    const more = (node.employees || []).length > 4
                        ? ` +${node.employees.length - 4} more`
                        : "";

                    return `
                        <div style="
                            width:100%;height:100%;
                            display:flex;flex-direction:column;
                            border-radius:8px;overflow:hidden;
                            font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
                            box-shadow:0 1px 4px rgba(0,0,0,.12);
                            cursor:pointer;
                        ">
                            <div style="
                                background:linear-gradient(135deg,#4f46e5,#7c3aed);
                                color:#fff;padding:8px 12px;
                                font-weight:600;font-size:13px;
                                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
                            ">
                                ${this._escapeHtml(node.name)}
                            </div>
                            <div style="
                                flex:1;background:#fff;padding:8px 12px;
                                font-size:11px;color:#4b5563;
                                display:flex;flex-direction:column;gap:4px;
                            ">
                                <div style="display:flex;align-items:center;gap:4px;">
                                    <span style="color:#9ca3af;">🏢</span>
                                    <span>${this._escapeHtml(dept)}</span>
                                </div>
                                <div style="display:flex;align-items:center;gap:4px;">
                                    <span style="color:#9ca3af;">👥</span>
                                    <span style="font-weight:600;color:#4f46e5;">${empCount}</span>
                                    <span>employee${empCount !== 1 ? 's' : ''}</span>
                                </div>
                                ${empNames ? `
                                <div style="
                                    font-size:10px;color:#9ca3af;
                                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
                                    margin-top:2px;
                                ">
                                    ${this._escapeHtml(empNames)}${more}
                                </div>` : ''}
                            </div>
                        </div>
                    `;
                })
                .render();
        } catch (e) {
            this.state.error = e.message;
            console.error("d3-org-chart render error:", e);
        }
    }

    /** Escape HTML to prevent XSS in node content */
    _escapeHtml(str) {
        if (!str) return "";
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }
}

OrgStructure.template = "hcm.OrgStructure";
OrgStructure.props = {};
registry.category("actions").add("hcm_org_structure", OrgStructure);
