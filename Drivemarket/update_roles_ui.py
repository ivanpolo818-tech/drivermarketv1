import re
import os

crear_file = r"d:\samuel proyec\Proyect\Drivemarket\templates\admin\admin_crear_usuario.html"
editar_file = r"d:\samuel proyec\Proyect\Drivemarket\templates\admin\usuario_editar.html"

def update_crear():
    with open(crear_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Update HTML roles
    html_roles = """                <div class="role-cards" id="roleCards">
                  <label class="role-card role-comprador active" data-val="comprador">
                    <input type="radio" name="rol" value="comprador" checked onchange="updatePreview()">
                    <div class="rc-icon"><i class="fas fa-user"></i></div>
                    <div class="rc-body"><b>Comprador</b><p>Usuario estándar</p></div>
                    <i class="fas fa-check-circle rc-check"></i>
                  </label>
                  <label class="role-card role-vendedor" data-val="vendedor">
                    <input type="radio" name="rol" value="vendedor" onchange="updatePreview()">
                    <div class="rc-icon"><i class="fas fa-store"></i></div>
                    <div class="rc-body"><b>Vendedor</b><p>Publica sus vehículos</p></div>
                    <i class="fas fa-check-circle rc-check"></i>
                  </label>
                  <label class="role-card role-editor" data-val="editor">
                    <input type="radio" name="rol" value="editor" onchange="updatePreview()">
                    <div class="rc-icon"><i class="fas fa-pen"></i></div>
                    <div class="rc-body"><b>Editor</b><p>Gestiona categorías</p></div>
                    <i class="fas fa-check-circle rc-check"></i>
                  </label>
                  <label class="role-card role-moderador" data-val="moderador">
                    <input type="radio" name="rol" value="moderador" onchange="updatePreview()">
                    <div class="rc-icon"><i class="fas fa-shield-alt"></i></div>
                    <div class="rc-body"><b>Moderador</b><p>Gestiona reportes</p></div>
                    <i class="fas fa-check-circle rc-check"></i>
                  </label>
                  <label class="role-card role-admin" data-val="admin">
                    <input type="radio" name="rol" value="admin" onchange="updatePreview()">
                    <div class="rc-icon"><i class="fas fa-crown"></i></div>
                    <div class="rc-body"><b>Admin</b><p>Gestión avanzada</p></div>
                    <i class="fas fa-check-circle rc-check"></i>
                  </label>
                  <label class="role-card role-superadmin" data-val="superadmin">
                    <input type="radio" name="rol" value="superadmin" onchange="updatePreview()">
                    <div class="rc-icon"><i class="fas fa-gem"></i></div>
                    <div class="rc-body"><b>Superadmin</b><p>Control total</p></div>
                    <i class="fas fa-check-circle rc-check"></i>
                  </label>
                </div>"""
    
    content = re.sub(r'<div class="role-cards" id="roleCards">.*?</div>\s+</div>', html_roles + '\n              </div>', content, flags=re.DOTALL)
    
    # Update default reset focus
    content = content.replace('.role-card[data-val="user"]', '.role-card[data-val="comprador"]')

    # 2. Update CSS
    css_icons = """.role-comprador .rc-icon{background:rgba(99,102,241,.1);color:var(--primary);}
.role-vendedor .rc-icon{background:rgba(16,185,129,.1);color:#059669;}
.role-editor .rc-icon{background:rgba(245,158,11,.1);color:#f59e0b;}
.role-moderador .rc-icon{background:rgba(59,130,246,.1);color:#3b82f6;}
.role-admin .rc-icon{background:rgba(239,68,68,.1);color:#dc2626;}
.role-superadmin .rc-icon{background:rgba(71,85,105,.1);color:#475569;}"""
    
    content = re.sub(r'\.role-user \.rc-icon\{.*?\.role-admin \.rc-icon\{.*?\}', css_icons, content, flags=re.DOTALL)
    
    css_active = """.role-card.active{border-color:var(--primary);background:color-mix(in srgb,var(--primary) 6%,transparent);box-shadow:0 0 0 3px rgba(99,102,241,.1);}
.role-card.active .rc-check{opacity:1;}
.role-admin.active{border-color:#dc2626;background:rgba(239,68,68,.05);box-shadow:0 0 0 3px rgba(239,68,68,.1);}
.role-admin.active .rc-check{color:#dc2626;}
.role-vendedor.active{border-color:#059669;background:rgba(16,185,129,.05);box-shadow:0 0 0 3px rgba(16,185,129,.1);}
.role-vendedor.active .rc-check{color:#059669;}
.role-editor.active{border-color:#f59e0b;background:rgba(245,158,11,.05);box-shadow:0 0 0 3px rgba(245,158,11,.1);}
.role-editor.active .rc-check{color:#f59e0b;}
.role-moderador.active{border-color:#3b82f6;background:rgba(59,130,246,.05);box-shadow:0 0 0 3px rgba(59,130,246,.1);}
.role-moderador.active .rc-check{color:#3b82f6;}
.role-superadmin.active{border-color:#475569;background:rgba(71,85,105,.05);box-shadow:0 0 0 3px rgba(71,85,105,.1);}
.role-superadmin.active .rc-check{color:#475569;}"""
    
    content = re.sub(r'\.role-card\.active\{.*?\.role-vendedor\.active \.rc-check\{.*?\}', css_active, content, flags=re.DOTALL)
    
    # 3. Update JS roleMap & gradMap
    js_maps = """  var roleMap = {
    comprador: {label:'Comprador', icon:'fa-user',  color:'rgba(99,102,241,.1)', textColor:'#6366f1'},
    vendedor:  {label:'Vendedor',  icon:'fa-store', color:'rgba(16,185,129,.1)', textColor:'#059669'},
    editor:    {label:'Editor',    icon:'fa-pen',   color:'rgba(245,158,11,.1)', textColor:'#f59e0b'},
    moderador: {label:'Moderador', icon:'fa-shield-alt', color:'rgba(59,130,246,.1)', textColor:'#3b82f6'},
    admin:     {label:'Administrador', icon:'fa-crown', color:'rgba(239,68,68,.1)', textColor:'#dc2626'},
    superadmin:{label:'Superadmin',icon:'fa-gem',   color:'rgba(71,85,105,.1)', textColor:'#475569'}
  };
  var r = roleMap[rol] || roleMap['comprador'];
  var roleEl = document.getElementById('previewRole');
  roleEl.innerHTML = '<i class="fas '+r.icon+'"></i> '+r.label;
  roleEl.style.background = r.color;
  roleEl.style.color = r.textColor;
  roleEl.style.borderColor = r.textColor.replace(')',', .25)').replace('rgb','rgba').replace('#','');
  var gradMap = {
    comprador: 'linear-gradient(135deg,#6366f1,#a855f7)',
    vendedor:  'linear-gradient(135deg,#10b981,#059669)',
    editor:    'linear-gradient(135deg,#f59e0b,#d97706)',
    moderador: 'linear-gradient(135deg,#3b82f6,#2563eb)',
    admin:     'linear-gradient(135deg,#ef4444,#dc2626)',
    superadmin:'linear-gradient(135deg,#475569,#1e293b)'
  };
  document.getElementById('avatarPreview').style.background = gradMap[rol] || gradMap['comprador'];"""
    
    content = re.sub(r'  var roleMap = \{.*?(document\.getElementById\(\'avatarPreview\'\)\.style\.background = gradMap\[rol\] \|\| gradMap\[\'user\'\];)', js_maps, content, flags=re.DOTALL)
    
    content = content.replace("|| {value:'user'}", "|| {value:'comprador'}")
    
    with open(crear_file, 'w', encoding='utf-8') as f:
        f.write(content)

def update_editar():
    with open(editar_file, 'r', encoding='utf-8') as f:
        content = f.read()

    html_roles = """                <div class="role-cards" id="roleCards">
                  <label class="role-card role-comprador {{ 'rc-active' if usuario.rol == 'comprador' else '' }}" data-val="comprador">
                    <input type="radio" name="rol" value="comprador" {{ 'checked' if usuario.rol == 'comprador' else '' }} onchange="markDirty();updatePreview()">
                    <div class="rc-icon"><i class="fas fa-user"></i></div>
                    <div class="rc-body"><b>Comprador</b></div>
                    <i class="fas fa-check-circle rc-chk"></i>
                  </label>
                  <label class="role-card role-vendedor {{ 'rc-active' if usuario.rol == 'vendedor' else '' }}" data-val="vendedor">
                    <input type="radio" name="rol" value="vendedor" {{ 'checked' if usuario.rol == 'vendedor' else '' }} onchange="markDirty();updatePreview()">
                    <div class="rc-icon"><i class="fas fa-store"></i></div>
                    <div class="rc-body"><b>Vendedor</b></div>
                    <i class="fas fa-check-circle rc-chk"></i>
                  </label>
                  <label class="role-card role-editor {{ 'rc-active rc-editor-active' if usuario.rol == 'editor' else '' }}" data-val="editor">
                    <input type="radio" name="rol" value="editor" {{ 'checked' if usuario.rol == 'editor' else '' }} onchange="markDirty();updatePreview()">
                    <div class="rc-icon"><i class="fas fa-pen"></i></div>
                    <div class="rc-body"><b>Editor</b></div>
                    <i class="fas fa-check-circle rc-chk"></i>
                  </label>
                  <label class="role-card role-moderador {{ 'rc-active rc-moderador-active' if usuario.rol == 'moderador' else '' }}" data-val="moderador">
                    <input type="radio" name="rol" value="moderador" {{ 'checked' if usuario.rol == 'moderador' else '' }} onchange="markDirty();updatePreview()">
                    <div class="rc-icon"><i class="fas fa-shield-alt"></i></div>
                    <div class="rc-body"><b>Moderador</b></div>
                    <i class="fas fa-check-circle rc-chk"></i>
                  </label>
                  <label class="role-card role-admin {{ 'rc-active rc-admin-active' if usuario.rol == 'admin' else '' }}" data-val="admin">
                    <input type="radio" name="rol" value="admin" {{ 'checked' if usuario.rol == 'admin' else '' }} onchange="markDirty();updatePreview()">
                    <div class="rc-icon"><i class="fas fa-crown"></i></div>
                    <div class="rc-body"><b>Admin</b></div>
                    <i class="fas fa-check-circle rc-chk"></i>
                  </label>
                  <label class="role-card role-superadmin {{ 'rc-active rc-superadmin-active' if usuario.rol == 'superadmin' else '' }}" data-val="superadmin">
                    <input type="radio" name="rol" value="superadmin" {{ 'checked' if usuario.rol == 'superadmin' else '' }} onchange="markDirty();updatePreview()">
                    <div class="rc-icon"><i class="fas fa-gem"></i></div>
                    <div class="rc-body"><b>Superadmin</b></div>
                    <i class="fas fa-check-circle rc-chk"></i>
                  </label>
                </div>"""
                
    content = re.sub(r'<div class="role-cards" id="roleCards">.*?</div>\s+</div>', html_roles + '\n              </div>', content, flags=re.DOTALL)
    
    # css icons
    css_icons = """.role-comprador .rc-icon{background:rgba(99,102,241,.1);color:var(--primary);}
.role-vendedor .rc-icon{background:rgba(16,185,129,.1);color:#059669;}
.role-editor .rc-icon{background:rgba(245,158,11,.1);color:#f59e0b;}
.role-moderador .rc-icon{background:rgba(59,130,246,.1);color:#3b82f6;}
.role-admin .rc-icon{background:rgba(239,68,68,.1);color:#dc2626;}
.role-superadmin .rc-icon{background:rgba(71,85,105,.1);color:#475569;}"""
    
    content = re.sub(r'\.role-user \.rc-icon\{.*?\.role-admin \.rc-icon\{.*?\}', css_icons, content, flags=re.DOTALL)
    
    css_active = """.rc-active{border-color:var(--primary);background:color-mix(in srgb,var(--primary) 6%,transparent);box-shadow:0 0 0 3px rgba(99,102,241,.1);}
.rc-active .rc-chk{opacity:1;}
.rc-admin-active{border-color:#dc2626;background:rgba(239,68,68,.05);box-shadow:0 0 0 3px rgba(239,68,68,.1);}
.rc-admin-active .rc-chk{color:#dc2626;}
.rc-editor-active{border-color:#f59e0b;background:rgba(245,158,11,.05);box-shadow:0 0 0 3px rgba(245,158,11,.1);}
.rc-editor-active .rc-chk{color:#f59e0b;}
.rc-moderador-active{border-color:#3b82f6;background:rgba(59,130,246,.05);box-shadow:0 0 0 3px rgba(59,130,246,.1);}
.rc-moderador-active .rc-chk{color:#3b82f6;}
.rc-superadmin-active{border-color:#475569;background:rgba(71,85,105,.05);box-shadow:0 0 0 3px rgba(71,85,105,.1);}
.rc-superadmin-active .rc-chk{color:#475569;}"""
    content = re.sub(r'\.rc-active\{.*?\.rc-admin-active \.rc-chk\{.*?\}', css_active, content, flags=re.DOTALL)
    
    # js 
    js_update = """var rolColors={comprador:'linear-gradient(135deg,#6366f1,#a855f7)',vendedor:'linear-gradient(135deg,#10b981,#059669)',editor:'linear-gradient(135deg,#f59e0b,#d97706)',moderador:'linear-gradient(135deg,#3b82f6,#2563eb)',admin:'linear-gradient(135deg,#ef4444,#dc2626)',superadmin:'linear-gradient(135deg,#475569,#1e293b)'};
var rolLabels={comprador:'Comprador',vendedor:'Vendedor',editor:'Editor',moderador:'Moderador',admin:'Administrador',superadmin:'Superadmin'};
var rolIcons={comprador:'fa-user',vendedor:'fa-store',editor:'fa-pen',moderador:'fa-shield-alt',admin:'fa-crown',superadmin:'fa-gem'};"""

    content = re.sub(r'var rolColors=\{.*?\};\nvar rolLabels=\{.*?\};\nvar rolIcons=\{.*?\};', js_update, content, flags=re.DOTALL)
    
    content = content.replace("c.classList.remove('rc-active','rc-admin-active');", "c.classList.remove('rc-active','rc-admin-active','rc-editor-active','rc-moderador-active','rc-superadmin-active');")
    content = content.replace("if(card.getAttribute('data-val')==='admin') card.classList.add('rc-admin-active');", "if(card.getAttribute('data-val')==='admin') card.classList.add('rc-admin-active'); else if(card.getAttribute('data-val')==='editor') card.classList.add('rc-editor-active'); else if(card.getAttribute('data-val')==='moderador') card.classList.add('rc-moderador-active'); else if(card.getAttribute('data-val')==='superadmin') card.classList.add('rc-superadmin-active');")
    
    content = content.replace("||{value:'user'}", "||{value:'comprador'}")
    content = content.replace("rolColors.user", "rolColors.comprador")

    with open(editar_file, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    update_crear()
    update_editar()
    print("UI views updated successfully.")

