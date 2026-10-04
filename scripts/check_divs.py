with open('templates/bookings/new_booking.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

tokens = []
for m in re.finditer(r'(<div\b[^>]*>|</div>)', text):
    tag = m.group(1)
    pos = m.start()
    line_no = text[:pos].count('\n') + 1
    tokens.append((line_no, tag))

stack = []
for line_no, tag in tokens:
    if tag.startswith('<div'):
        m_id = re.search(r'id=["\']([^"\']+)["\']', tag)
        m_cls = re.search(r'class=["\']([^"\']+)["\']', tag)
        desc = (m_id.group(1) if m_id else '') or (m_cls.group(1) if m_cls else '') or tag[:25]
        stack.append((line_no, desc))
    else:
        if stack:
            popped = stack.pop()
            if 'stepPane' in popped[1] or 'bookingWizardApp' in popped[1]:
                print(f"Closed {popped[1]} (opened line {popped[0]}) at line {line_no}")
        else:
            print(f"EXTRA CLOSING </div> at line {line_no}")

print(f"\nRemaining unclosed divs at end: {len(stack)}")
for item in stack:
    print(item)
