# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# ¡NO IMPORTES 'app' AQUÍ PARA EVITAR IMPORTACIONES CIRCULARES!
db = SQLAlchemy()

# --- TUS MODELOS EXISTENTES ---

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    # ... resto de campos de usuario (email, password, etc.) ...
    
    # Relación: Un usuario tiene un solo perfil de vendedor (uselist=False)
    perfil_vendedor = db.relationship('PerfilVendedor', backref='usuario', uselist=False)
    
    # Relaciones con las nuevas tablas del chatbot
    conversaciones_chatbot = db.relationship('ConversacionChatbot', backref='usuario', lazy=True)
    faqs_creadas = db.relationship('FAQ', foreign_keys='FAQ.creado_por', backref='creador', lazy=True)

class PerfilVendedor(db.Model):
    __tablename__ = 'perfil_vendedor'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), unique=True, nullable=False)
    
    # --- 1. Información Comercial ---
    nombre_tienda = db.Column(db.String(100), nullable=False)
    email_comercial = db.Column(db.String(100), nullable=False)  # <-- NUEVO: Correo visible para clientes
    telefono_contacto = db.Column(db.String(20), nullable=False)
    descripcion = db.Column(db.Text)
    
    # --- 2. Información Legal (KYC) ---
    numero_id = db.Column(db.String(50), nullable=False)  # <-- NUEVO: Cédula o NIT
    
    # --- 3. Documentos de Verificación y Branding ---
    foto_id_frontal = db.Column(db.String(255))  # <-- NUEVO: Ruta de la imagen frontal
    foto_id_trasera = db.Column(db.String(255))  # <-- NUEVO: Ruta de la imagen trasera
    foto_portada = db.Column(db.String(255), nullable=True) # <-- NUEVO: Foto de cabecera pública de la tienda
    
    # --- 4. Estado y Seguridad ---
    # Valores esperados: 'pendiente', 'aprobado', 'rechazado'
    estado_verificacion = db.Column(db.String(20), default='pendiente') # <-- NUEVO
    
    # --- 5. Datos Bancarios (Mantener si ya los usabas) ---
    banco = db.Column(db.String(50))
    numero_cuenta = db.Column(db.String(50))

    def __repr__(self):
        return f'<Tienda {self.nombre_tienda} | Estado: {self.estado_verificacion}>'

# --- NUEVOS MODELOS PARA EL CHATBOT ---

class FAQ(db.Model):
    """Modelo para FAQs dinámicas del chatbot"""
    __tablename__ = 'faqs'
    
    id = db.Column(db.Integer, primary_key=True)
    pregunta = db.Column(db.String(500), nullable=False)
    respuesta = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(100), default='general')
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)
    creado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Índices para mejorar búsquedas
    __table_args__ = (
        db.Index('idx_faq_categoria', 'categoria'),
        db.Index('idx_faq_activo', 'activo'),
        db.Index('idx_faq_orden', 'orden'),
    )
    
    def __repr__(self):
        return f'<FAQ {self.id}: {self.pregunta[:30]}...>'

class ConversacionChatbot(db.Model):
    """Modelo para guardar conversaciones del chatbot"""
    __tablename__ = 'conversaciones_chatbot'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    session_id = db.Column(db.String(100), nullable=False)
    pregunta = db.Column(db.Text, nullable=False)
    respuesta = db.Column(db.Text, nullable=False)
    tipo_respuesta = db.Column(db.String(20), default='faq')  # faq, ia, error, humano
    feedback = db.Column(db.Boolean, nullable=True)  # True = útil, False = no útil
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Índices para mejorar búsquedas
    __table_args__ = (
        db.Index('idx_chat_usuario', 'usuario_id'),
        db.Index('idx_chat_session', 'session_id'),
        db.Index('idx_chat_tipo', 'tipo_respuesta'),
        db.Index('idx_chat_feedback', 'feedback'),
        db.Index('idx_chat_fecha', 'fecha'),
    )
    
    def __repr__(self):
        return f'<Conversacion {self.id}: {self.pregunta[:30]}... -> {self.tipo_respuesta}>'

# --- MODELO ADICIONAL: Alertas de Precio (si lo necesitas) ---
class AlertaPrecio(db.Model):
    """Modelo para alertas de precio de vehículos"""
    __tablename__ = 'alertas_precio'
    
    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    id_vehiculo = db.Column(db.Integer, nullable=False)  # Asumiendo que tienes tabla vehiculos
    precio_referencia = db.Column(db.Numeric(12, 2), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    notificado = db.Column(db.Boolean, default=False)
    fecha_notificacion = db.Column(db.DateTime, nullable=True)
    
    # Relación con usuario
    usuario = db.relationship('Usuario', backref='alertas_precio')
    
    # Índices y constraints
    __table_args__ = (
        db.UniqueConstraint('id_usuario', 'id_vehiculo', name='unique_alerta_usuario_vehiculo'),
        db.Index('idx_alerta_usuario', 'id_usuario'),
        db.Index('idx_alerta_vehiculo', 'id_vehiculo'),
        db.Index('idx_alerta_notificado', 'notificado'),
    )
    
    def __repr__(self):
        return f'<Alerta {self.id}: Usuario {self.id_usuario} - Vehículo {self.id_vehiculo}>'

# --- MODELOS PARA VEHÍCULOS ---

class Marca(db.Model):
    """Modelo para marcas de vehículos"""
    __tablename__ = 'marcas'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    logo = db.Column(db.String(255))
    
    # Relación con vehículos
    vehiculos = db.relationship('Vehiculo', backref='marca', lazy=True)
    
    def __repr__(self):
        return f'<Marca {self.nombre}>'

class Modelo(db.Model):
    """Modelo para modelos de vehículos"""
    __tablename__ = 'modelos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    
    # Relación con vehículos
    vehiculos = db.relationship('Vehiculo', backref='modelo', lazy=True)
    
    def __repr__(self):
        return f'<Modelo {self.nombre}>'

class Vehiculo(db.Model):
    """Modelo para vehículos en la base de datos"""
    __tablename__ = 'vehiculos'
    
    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    id_tipo = db.Column(db.Integer, nullable=True)
    id_marca = db.Column(db.Integer, db.ForeignKey('marcas.id'), nullable=True)
    id_modelo = db.Column(db.Integer, db.ForeignKey('modelos.id'), nullable=True)
    version = db.Column(db.String(100))
    id_color = db.Column(db.Integer, nullable=True)
    anio = db.Column(db.Integer)
    placa = db.Column(db.String(10))
    ciudad_placa = db.Column(db.String(100))
    ciudad_venta = db.Column(db.String(100))
    dueno = db.Column(db.String(10), default='Si')  # Enum: Si/No
    kilometraje = db.Column(db.Integer)
    transmision = db.Column(db.String(50), default='Manual')
    combustible = db.Column(db.String(50), default='Gasolina')
    motor = db.Column(db.String(50))
    traccion = db.Column(db.String(50))
    puertas = db.Column(db.Integer)
    precio = db.Column(db.Numeric(12, 2))
    negociable = db.Column(db.String(10), default='Si')  # Enum: Si/No
    imagen = db.Column(db.String(255))
    fecha_publicacion = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='disponible')  # disponible, vendido, pausado
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    vistas = db.Column(db.Integer, default=0)
    slug = db.Column(db.String(255), unique=True, index=True)
    descripcion = db.Column(db.Text)
    
    # --- MONETIZACIÓN: ANUNCIOS DESTACADOS MANUALES ---
    plan_destacado = db.Column(db.Boolean, default=False)
    comprobante_pago = db.Column(db.String(255), nullable=True)
    estado_pago = db.Column(db.String(20), default='ninguno') # ninguno, pendiente, aprobado, rechazado
    fecha_fin_destacado = db.Column(db.DateTime, nullable=True)

    
    # Índices para búsquedas
    __table_args__ = (
        db.Index('idx_vehiculo_marca', 'id_marca'),
        db.Index('idx_vehiculo_modelo', 'id_modelo'),
        db.Index('idx_vehiculo_precio', 'precio'),
        db.Index('idx_vehiculo_anio', 'anio'),
        db.Index('idx_vehiculo_estado', 'estado'),
        db.Index('idx_vehiculo_slug', 'slug'),
    )
    
    def __repr__(self):
        marca_nombre = self.marca.nombre if self.marca else 'N/A'
        modelo_nombre = self.modelo.nombre if self.modelo else 'N/A'
        return f'<Vehiculo {marca_nombre} {modelo_nombre} {self.anio} | Slug: {self.slug}>'
