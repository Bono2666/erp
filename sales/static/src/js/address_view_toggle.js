/** @odoo-module **/

var FIELDS = ['sold_to_ids', 'ship_to_ids', 'bill_to_ids'];

var ICONS = {
    'sold_to_ids': 'sales/static/src/img/contact.png',
    'ship_to_ids': 'general/static/src/img/shipping.png',
    'bill_to_ids': 'sales/static/src/img/invoice.png',
};

function buildKanbanHtml(fname) {
    var listWrapper = document.querySelector('[name="' + fname + '"]');
    if (!listWrapper) return '';
    var trs = listWrapper.querySelectorAll('tbody tr');
    var cards = [];
    var iconSrc = ICONS[fname] || '';
    for (var i = 0; i < trs.length; i++) {
        var cells = trs[i].querySelectorAll('td');
        if (cells.length < 2) continue;
        var id = cells[0] ? cells[0].textContent.trim() : '';
        var name = cells[1] ? cells[1].textContent.trim() : '';
        var district = cells[2] ? cells[2].textContent.trim() : '';
        var city = cells[3] ? cells[3].textContent.trim() : '';
        var state = cells[4] ? cells[4].textContent.trim() : '';
        var postal = cells[5] ? cells[5].textContent.trim() : '';
        var country = cells[6] ? cells[6].textContent.trim() : '';
        var addr = [district, city, state, postal, country].filter(Boolean).join(', ');

        cards.push(
            '<div class="o_kanban_record oe_kanban_global_click o_kanban_record_has_image_fill">' +
            '<div class="o_kanban_image">' +
            '<img alt="Image" src="/' + iconSrc + '"/>' +
            '</div>' +
            '<div class="oe_kanban_details">' +
            '<strong>' + name + '</strong>' +
            '<div>' + addr + '</div>' +
            '</div>' +
            '</div>'
        );
    }
    if (cards.length === 0) return '<div style="padding:20px;color:#999;text-align:center">No records</div>';
    return '<div class="o_kanban_renderer o_kanban_card_has_image_fill">' + cards.join('') + '</div>';
}

function scanAndInject() {
    var all = document.querySelectorAll('.tab-pane');
    for (var i = 0; i < all.length; i++) {
        var pane = all[i];
        var w = pane.querySelector('.o_field_one2many');
        if (!w) continue;

        var fname = w.getAttribute('name') || '';
        if (FIELDS.indexOf(fname) === -1) continue;

        if (w.querySelector('.address-view-toggle')) continue;

        var le = w.querySelector('.o_list_view');
        var ke = w.querySelector('.o_kanban_view');
        if (!le && !ke) continue;

        var cp = w.querySelector('.o_x2m_control_panel');
        if (cp) cp.style.display = 'none';

        var bar = document.createElement('div');
        bar.className = 'address-view-toggle';

        var b1 = document.createElement('button');
        b1.className = 'address-toggle-btn active';
        b1.setAttribute('data-v', 'list');
        b1.innerHTML = '<i class="fa fa-list"></i> List';
        bar.appendChild(b1);

        var b2 = document.createElement('button');
        b2.className = 'address-toggle-btn';
        b2.setAttribute('data-v', 'kanban');
        b2.innerHTML = '<i class="fa fa-th"></i> Kanban';
        bar.appendChild(b2);

        var kanbanDiv = document.createElement('div');
        kanbanDiv.className = 'address-kanban-view';
        kanbanDiv.style.display = 'none';
        kanbanDiv.innerHTML = buildKanbanHtml(fname);

        w.insertBefore(bar, w.firstChild);
        if (le) {
            w.insertBefore(kanbanDiv, le.nextSibling);
        }

        (function(leRef, keRef, kDiv) {
            var btns = bar.querySelectorAll('.address-toggle-btn');
            for (var j = 0; j < btns.length; j++) {
                btns[j].addEventListener('click', function() {
                    for (var k = 0; k < btns.length; k++) btns[k].classList.remove('active');
                    this.classList.add('active');
                    var v = this.getAttribute('data-v');
                    if (v === 'list') {
                        if (leRef) leRef.style.display = '';
                        if (keRef) keRef.style.display = 'none';
                        kDiv.style.display = 'none';
                    } else {
                        if (leRef) leRef.style.display = 'none';
                        if (keRef) keRef.style.display = 'none';
                        kDiv.style.display = '';
                    }
                });
            }
        })(le, ke, kanbanDiv);
    }
}

setInterval(scanAndInject, 1500);
