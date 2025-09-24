import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from io import BytesIO

# Cargar variables de entorno
load_dotenv()

class PlanningPokerApp:
    def __init__(self):
        """Inicializa Planning Poker con conexión a Supabase"""
        # Configurar Supabase
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            st.error("❌ Configura SUPABASE_URL y SUPABASE_ANON_KEY en tu archivo .env")
            st.stop()
        
        try:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
        except Exception as e:
            st.error(f"❌ Error conectando a Supabase: {e}")
            st.stop()
        
        self.fibonacci_cards = [0, 0.5, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
        self.special_cards = ['?', '∞']
        
        # Inicializar session state
        if 'current_session_id' not in st.session_state:
            st.session_state.current_session_id = None
        if 'session_name' not in st.session_state:
            st.session_state.session_name = ""

    def create_session(self, name, facilitator):
        """Crea nueva sesión"""
        try:
            session_data = {
                'name': name,
                'facilitator': facilitator,
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }
            
            result = self.supabase.table('poker_sessions').insert(session_data).execute()
            
            if result.data:
                st.session_state.current_session_id = result.data[0]['id']
                st.session_state.session_name = name
                return True
            return False
        except Exception as e:
            st.error(f"Error creando sesión: {e}")
            return False

    def get_sessions_df(self):
        """Obtiene DataFrame de sesiones"""
        try:
            result = self.supabase.table('poker_sessions').select('*').order('created_at', desc=True).execute()
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except:
            return pd.DataFrame()

    def get_participants_df(self, session_id):
        """Obtiene DataFrame de participantes"""
        try:
            result = self.supabase.table('participants').select('*').eq('session_id', session_id).execute()
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except:
            return pd.DataFrame()

    def get_stories_df(self, session_id):
        """Obtiene DataFrame de historias"""
        try:
            result = self.supabase.table('user_stories').select('*').eq('session_id', session_id).execute()
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except:
            return pd.DataFrame()

    def add_participant(self, name, role, email):
        """Añade participante"""
        try:
            participant_data = {
                'session_id': st.session_state.current_session_id,
                'name': name,
                'role': role,
                'email': email,
                'joined_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table('participants').insert(participant_data).execute()
            return bool(result.data)
        except Exception as e:
            st.error(f"Error añadiendo participante: {e}")
            return False

    def add_story(self, story_id, title, description, criteria, priority):
        """Añade historia de usuario"""
        try:
            story_data = {
                'session_id': st.session_state.current_session_id,
                'story_id': story_id,
                'title': title,
                'description': description,
                'acceptance_criteria': criteria,
                'priority': priority,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table('user_stories').insert(story_data).execute()
            return bool(result.data)
        except Exception as e:
            st.error(f"Error añadiendo historia: {e}")
            return False

    def save_estimates(self, story_db_id, estimates_dict):
        """Guarda estimaciones"""
        try:
            participants_df = self.get_participants_df(st.session_state.current_session_id)
            
            estimates_data = []
            for participant_name, estimate in estimates_dict.items():
                participant_row = participants_df[participants_df['name'] == participant_name]
                if not participant_row.empty:
                    participant_id = participant_row.iloc[0]['id']
                    
                    estimates_data.append({
                        'session_id': st.session_state.current_session_id,
                        'story_id': story_db_id,
                        'participant_id': participant_id,
                        'estimate': str(estimate),
                        'estimated_at': datetime.now().isoformat()
                    })
            
            if estimates_data:
                result = self.supabase.table('estimates').insert(estimates_data).execute()
                return bool(result.data)
            return False
        except Exception as e:
            st.error(f"Error guardando estimaciones: {e}")
            return False

    def get_estimates_df(self, session_id):
        """Obtiene DataFrame de estimaciones con información enriquecida"""
        try:
            estimates_result = self.supabase.table('estimates').select('*').eq('session_id', session_id).execute()
            if not estimates_result.data:
                return pd.DataFrame()
            
            estimates_data = []
            for estimate in estimates_result.data:
                # Obtener participante
                participant_result = self.supabase.table('participants').select('name, role').eq('id', estimate['participant_id']).execute()
                participant_name = participant_result.data[0]['name'] if participant_result.data else 'Desconocido'
                participant_role = participant_result.data[0]['role'] if participant_result.data else 'N/A'
                
                # Obtener historia
                story_result = self.supabase.table('user_stories').select('story_id, title').eq('id', estimate['story_id']).execute()
                story_id = story_result.data[0]['story_id'] if story_result.data else 'N/A'
                story_title = story_result.data[0]['title'] if story_result.data else 'N/A'
                
                estimates_data.append({
                    'story_id': story_id,
                    'story_title': story_title,
                    'participant_name': participant_name,
                    'participant_role': participant_role,
                    'estimate': estimate['estimate'],
                    'estimated_at': estimate['estimated_at']
                })
            
            return pd.DataFrame(estimates_data)
        except Exception as e:
            st.error(f"Error obteniendo estimaciones: {e}")
            return pd.DataFrame()

def render_sidebar(poker):
    """Renderiza el sidebar con gestión de sesiones"""
    st.sidebar.header("🎯 Gestión de Sesiones")
    
    sessions_df = poker.get_sessions_df()
    
    # Cargar sesión existente
    if not sessions_df.empty:
        st.sidebar.subheader("📋 Sesiones Existentes")
        selected_session = st.sidebar.selectbox(
            "Selecciona una sesión:",
            options=sessions_df['id'].tolist(),
            format_func=lambda x: f"{sessions_df[sessions_df['id']==x]['name'].iloc[0]} - {sessions_df[sessions_df['id']==x]['facilitator'].iloc[0]}",
            key="session_selector"
        )
        
        if st.sidebar.button("🔄 Cargar Sesión"):
            st.session_state.current_session_id = selected_session
            st.session_state.session_name = sessions_df[sessions_df['id']==selected_session]['name'].iloc[0]
            st.success(f"✅ Sesión cargada: {st.session_state.session_name}")
            st.rerun()
    
    # Crear nueva sesión
    st.sidebar.subheader("➕ Nueva Sesión")
    with st.sidebar.form("new_session"):
        session_name = st.text_input("Nombre de la sesión")
        facilitator_name = st.text_input("Facilitador")
        
        if st.form_submit_button("🎲 Crear Sesión"):
            if session_name and facilitator_name:
                if poker.create_session(session_name, facilitator_name):
                    st.success(f"✅ Sesión '{session_name}' creada!")
                    st.rerun()
                else:
                    st.error("❌ Error creando la sesión")
            else:
                st.error("❌ Completa todos los campos")

def render_participants_tab(poker):
    """Renderiza la pestaña de participantes"""
    st.subheader("👥 Gestión de Participantes")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### ➕ Añadir Participante")
        with st.form("add_participant"):
            name = st.text_input("Nombre")
            role = st.selectbox("Rol", ["Developer", "Senior Developer", "Tech Lead", "Product Owner", "Scrum Master", "QA", "Designer"])
            email = st.text_input("Email (opcional)")
            
            if st.form_submit_button("➕ Añadir"):
                if name:
                    if poker.add_participant(name, role, email or None):
                        st.success(f"✅ {name} añadido!")
                        st.rerun()
                    else:
                        st.error("❌ Error añadiendo participante")
                else:
                    st.error("❌ El nombre es obligatorio")
    
    with col2:
        st.markdown("### 👥 Participantes Actuales")
        participants_df = poker.get_participants_df(st.session_state.current_session_id)
        
        if not participants_df.empty:
            # Métricas
            col1_metrics, col2_metrics, col3_metrics = st.columns(3)
            with col1_metrics:
                st.metric("Total", len(participants_df))
            with col2_metrics:
                st.metric("Roles", participants_df['role'].nunique())
            with col3_metrics:
                emails_count = participants_df['email'].notna().sum()
                st.metric("Con Email", emails_count)
            
            # DataFrame interactivo
            st.dataframe(
                participants_df[['name', 'role', 'email', 'joined_at']],
                use_container_width=True,
                hide_index=True
            )
            
            # Gráfico de roles
            if len(participants_df) > 1:
                role_counts = participants_df['role'].value_counts().reset_index()
                role_counts.columns = ['role', 'count']
                fig_roles = px.pie(
                    role_counts,
                    values='count',
                    names='role',
                    title="Distribución por Roles"
                )
                st.plotly_chart(fig_roles, use_container_width=True)
        else:
            st.info("👤 No hay participantes. Añade algunos para comenzar.")

def render_stories_tab(poker):
    """Renderiza la pestaña de historias de usuario"""
    st.subheader("📝 Gestión de Historias de Usuario")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### ➕ Añadir Historia")
        with st.form("add_story"):
            story_id = st.text_input("ID (ej: US-001)")
            title = st.text_input("Título")
            description = st.text_area("Descripción")
            criteria = st.text_area("Criterios de Aceptación")
            priority = st.selectbox("Prioridad", ["Low", "Medium", "High", "Critical"])
            
            if st.form_submit_button("📝 Añadir Historia"):
                if story_id and title:
                    if poker.add_story(story_id, title, description, criteria, priority):
                        st.success(f"✅ Historia {story_id} añadida!")
                        st.rerun()
                    else:
                        st.error("❌ Error añadiendo historia")
                else:
                    st.error("❌ ID y título son obligatorios")
    
    with col2:
        st.markdown("### 📋 Historias Actuales")
        stories_df = poker.get_stories_df(st.session_state.current_session_id)
        
        if not stories_df.empty:
            # Métricas de historias
            estimated_stories = stories_df[stories_df['status'] == 'estimated']
            total_points = estimated_stories['final_estimate'].sum() if 'final_estimate' in estimated_stories.columns and not estimated_stories.empty else 0
            
            col1_metrics, col2_metrics, col3_metrics = st.columns(3)
            with col1_metrics:
                st.metric("Total", len(stories_df))
            with col2_metrics:
                st.metric("Estimadas", len(estimated_stories))
            with col3_metrics:
                st.metric("Story Points", total_points or 0)
            
            # DataFrame de historias
            display_cols = ['story_id', 'title', 'priority', 'status', 'final_estimate']
            available_cols = [col for col in display_cols if col in stories_df.columns]
            st.dataframe(
                stories_df[available_cols],
                use_container_width=True,
                hide_index=True
            )
            
            # Gráfico de prioridades
            priority_counts = stories_df['priority'].value_counts().reset_index()
            priority_counts.columns = ['priority', 'count']
            fig_priority = px.bar(
                priority_counts,
                x='priority',
                y='count',
                title="Historias por Prioridad",
                color='priority'
            )
            st.plotly_chart(fig_priority, use_container_width=True)
        else:
            st.info("📝 No hay historias. Añade algunas para comenzar.")

def render_estimation_tab(poker):
    """Renderiza la pestaña de estimación"""
    st.subheader("🎯 Proceso de Estimación")
    
    stories_df = poker.get_stories_df(st.session_state.current_session_id)
    participants_df = poker.get_participants_df(st.session_state.current_session_id)
    
    if stories_df.empty:
        st.warning("📝 Primero añade algunas historias de usuario")
        return
    elif participants_df.empty:
        st.warning("👥 Primero añade algunos participantes")
        return
    
    # Seleccionar historia para estimar
    pending_stories = stories_df[stories_df['status'] == 'pending']
    
    if not pending_stories.empty:
        st.markdown("### 🎲 Selecciona Historia para Estimar")
        
        selected_story = st.selectbox(
            "Historia:",
            options=pending_stories['story_id'].tolist(),
            format_func=lambda x: f"{x} - {pending_stories[pending_stories['story_id']==x]['title'].iloc[0]}"
        )
        
        if selected_story:
            story_row = stories_df[stories_df['story_id'] == selected_story].iloc[0]
            
            # Mostrar detalles de la historia
            st.markdown(f"""
            **📋 {story_row['title']}**
            
            **Descripción:** {story_row['description']}
            
            **Criterios:** {story_row['acceptance_criteria']}
            
            **Prioridad:** {story_row['priority']}
            """)
            
            st.markdown("---")
            st.markdown("### 🃏 Cartas de Estimación")
            
            # Mostrar cartas disponibles
            all_cards = poker.fibonacci_cards + poker.special_cards
            cols = st.columns(len(all_cards))
            for i, card in enumerate(all_cards):
                with cols[i]:
                    st.markdown(f"""
                    <div style="border: 2px solid #e0e0e0; border-radius: 10px; padding: 1rem; margin: 0.5rem; text-align: center; background: #f8f9fa;">
                        <h3>{card}</h3>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("### 👥 Estimaciones de Participantes")
            
            estimates = {}
            for _, participant in participants_df.iterrows():
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.write(f"**{participant['name']}** ({participant['role']})")
                with col2:
                    estimate = st.selectbox(
                        f"Estimación",
                        options=all_cards,
                        key=f"estimate_{participant['id']}",
                        label_visibility="collapsed"
                    )
                    estimates[participant['name']] = estimate
            
            if st.button("🎯 Procesar Estimaciones", type="primary"):
                analyze_estimates(poker, story_row, estimates)
    else:
        st.info("✅ Todas las historias han sido estimadas")

def analyze_estimates(poker, story_row, estimates):
    """Analiza las estimaciones y guarda resultados"""
    numeric_estimates = []
    special_estimates = []
    
    for participant, estimate in estimates.items():
        if estimate in ['?', '∞']:
            special_estimates.append((participant, estimate))
        else:
            try:
                numeric_estimates.append((participant, float(estimate)))
            except:
                pass
    
    st.markdown("### 📊 Resultados de Estimación")
    
    # Mostrar todas las estimaciones
    results_df = pd.DataFrame(list(estimates.items()), columns=['Participante', 'Estimación'])
    st.dataframe(results_df, use_container_width=True, hide_index=True)
    
    if special_estimates:
        st.warning("⚠️ Estimaciones especiales:")
        for participant, estimate in special_estimates:
            meaning = "Necesita más información" if estimate == '?' else "Demasiado complejo"
            st.write(f"- **{participant}**: {estimate} ({meaning})")
    
    if len(numeric_estimates) > 1:
        values = [est[1] for est in numeric_estimates]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Mínimo", f"{min(values)}")
        with col2:
            st.metric("Máximo", f"{max(values)}")
        with col3:
            st.metric("Promedio", f"{np.mean(values):.1f}")
        
        # Gráfico de estimaciones
        fig = px.bar(
            x=[est[0] for est in numeric_estimates],
            y=[est[1] for est in numeric_estimates],
            title="Estimaciones por Participante",
            labels={'x': 'Participante', 'y': 'Estimación'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Verificar consenso
        unique_values = set(values)
        if len(unique_values) == 1:
            st.success(f"🎉 ¡CONSENSO! Todos estimaron: {values[0]}")
            
            # Guardar estimaciones
            if poker.save_estimates(story_row['id'], estimates):
                try:
                    poker.supabase.table('user_stories').update({
                        'status': 'estimated',
                        'final_estimate': values[0],
                        'last_estimated_at': datetime.now().isoformat()
                    }).eq('id', story_row['id']).execute()
                    
                    st.success("✅ Estimación guardada!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error actualizando historia: {e}")
        else:
            st.warning(f"🔄 Sin consenso. Rango: {min(values)} - {max(values)}")
            st.info("💬 Discutan las diferencias y vuelvan a estimar")

def render_analytics_tab(poker):
    """Renderiza la pestaña de analytics"""
    st.subheader("📊 Analytics de la Sesión")
    
    estimates_df = poker.get_estimates_df(st.session_state.current_session_id)
    
    if not estimates_df.empty:
        # Métricas generales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            unique_stories = estimates_df['story_id'].nunique()
            st.metric("Historias Estimadas", unique_stories)
        
        with col2:
            total_estimates = len(estimates_df)
            st.metric("Total Estimaciones", total_estimates)
        
        with col3:
            numeric_estimates = pd.to_numeric(estimates_df['estimate'], errors='coerce').dropna()
            avg_estimate = numeric_estimates.mean() if not numeric_estimates.empty else 0
            st.metric("Promedio", f"{avg_estimate:.1f}")
        
        with col4:
            participants_estimating = estimates_df['participant_name'].nunique()
            st.metric("Participantes Activos", participants_estimating)
        
        # Gráficos de análisis
        col1, col2 = st.columns(2)
        
        with col1:
            if not numeric_estimates.empty:
                fig_dist = px.histogram(
                    numeric_estimates,
                    nbins=20,
                    title="Distribución de Estimaciones"
                )
                st.plotly_chart(fig_dist, use_container_width=True)
        
        with col2:
            participant_stats = estimates_df.groupby('participant_name')['estimate'].apply(
                lambda x: pd.to_numeric(x, errors='coerce').mean()
            ).reset_index()
            participant_stats.columns = ['Participante', 'Promedio_Estimacion']
            participant_stats = participant_stats.dropna()
            
            if not participant_stats.empty:
                fig_participant = px.bar(
                    participant_stats,
                    x='Participante',
                    y='Promedio_Estimacion',
                    title="Promedio por Participante"
                )
                st.plotly_chart(fig_participant, use_container_width=True)
        
        # Tabla detallada
        st.markdown("### 📋 Detalle de Estimaciones")
        st.dataframe(
            estimates_df[['story_id', 'story_title', 'participant_name', 'participant_role', 'estimate', 'estimated_at']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("🎯 No hay estimaciones aún.")

def render_reports_tab(poker):
    """Renderiza la pestaña de reportes"""
    st.subheader("📈 Reportes y Exportación")
    
    # Obtener datos
    stories_df = poker.get_stories_df(st.session_state.current_session_id)
    participants_df = poker.get_participants_df(st.session_state.current_session_id)
    estimates_df = poker.get_estimates_df(st.session_state.current_session_id)
    
    st.markdown("### 📊 Resumen Ejecutivo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not stories_df.empty:
            estimated_stories = stories_df[stories_df['status'] == 'estimated']
            total_points = estimated_stories['final_estimate'].sum() if 'final_estimate' in estimated_stories.columns and not estimated_stories.empty else 0
            
            st.markdown(f"""
            **📋 Historias:**
            - Total: {len(stories_df)}
            - Estimadas: {len(estimated_stories)}
            - Pendientes: {len(stories_df) - len(estimated_stories)}
            - Story Points: {total_points}
            """)
    
    with col2:
        if not estimates_df.empty:
            numeric_estimates = pd.to_numeric(estimates_df['estimate'], errors='coerce').dropna()
            
            st.markdown(f"""
            **🎯 Estimaciones:**
            - Total: {len(estimates_df)}
            - Promedio: {numeric_estimates.mean():.1f}
            - Mediana: {numeric_estimates.median():.1f}
            - Participantes: {participants_df['name'].nunique() if not participants_df.empty else 0}
            """)
    
    # Exportación
    st.markdown("### 📁 Exportar Datos")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if not participants_df.empty:
            csv = participants_df.to_csv(index=False)
            st.download_button(
                label="📥 Participantes CSV",
                data=csv,
                file_name=f"participantes_{st.session_state.session_name}.csv",
                mime="text/csv"
            )
    
    with col2:
        if not stories_df.empty:
            csv = stories_df.to_csv(index=False)
            st.download_button(
                label="📥 Historias CSV",
                data=csv,
                file_name=f"historias_{st.session_state.session_name}.csv",
                mime="text/csv"
            )
    
    with col3:
        if not estimates_df.empty:
            csv = estimates_df.to_csv(index=False)
            st.download_button(
                label="📥 Estimaciones CSV",
                data=csv,
                file_name=f"estimaciones_{st.session_state.session_name}.csv",
                mime="text/csv"
            )
    
    # Reporte Excel completo
    if not stories_df.empty:
        st.markdown("### 📊 Reporte Excel Completo")
        
        if st.button("📋 Generar Reporte Excel"):
            try:
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    if not participants_df.empty:
                        participants_df.to_excel(writer, sheet_name='Participantes', index=False)
                    if not stories_df.empty:
                        stories_df.to_excel(writer, sheet_name='Historias', index=False)
                    if not estimates_df.empty:
                        estimates_df.to_excel(writer, sheet_name='Estimaciones', index=False)
                    
                    # Hoja de resumen
                    estimated_stories = stories_df[stories_df['status'] == 'estimated'] if not stories_df.empty else pd.DataFrame()
                    total_points = estimated_stories['final_estimate'].sum() if 'final_estimate' in estimated_stories.columns and not estimated_stories.empty else 0
                    
                    summary_data = {
                        'Métrica': ['Total Participantes', 'Total Historias', 'Historias Estimadas', 'Total Estimaciones', 'Story Points'],
                        'Valor': [
                            len(participants_df) if not participants_df.empty else 0,
                            len(stories_df) if not stories_df.empty else 0,
                            len(estimated_stories) if not estimated_stories.empty else 0,
                            len(estimates_df) if not estimates_df.empty else 0,
                            total_points
                        ]
                    }
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Resumen', index=False)
                
                buffer.seek(0)
                st.download_button(
                    label="📊 Descargar Reporte Excel",
                    data=buffer.read(),
                    file_name=f"reporte_planning_poker_{st.session_state.session_name}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error generando Excel: {e}")

def main():
    # Configurar página
    st.set_page_config(
        page_title="Planning Poker", 
        page_icon="🎲", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS personalizado
    st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title(" Planning Poker Dashboard")
    st.markdown("---")
    
    # Inicializar aplicación
    poker = PlanningPokerApp()
    
    # Sidebar
    render_sidebar(poker)
    
    # Contenido principal
    if st.session_state.current_session_id:
        st.header(f"📊 Sesión Activa: {st.session_state.session_name}")
        
        # Tabs principales
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "👥 Participantes", 
            "📝 Historias", 
            "🎯 Estimaciones", 
            "📊 Analytics", 
            
                    "📈 Reportes"
        ])

        with tab1:
            render_participants_tab(poker)

        with tab2:
            render_stories_tab(poker)

        with tab3:
            render_estimation_tab(poker)

        with tab4:
            render_analytics_tab(poker)

        with tab5:
            render_reports_tab(poker)

        # Controles de sesión en la parte superior del contenido
        st.markdown("---")
        col_left, col_right = st.columns([3, 1])
        with col_left:
            st.write(f"**Sesión:** {st.session_state.session_name} (ID: {st.session_state.current_session_id})")
        with col_right:
            if st.button("🔒 Cerrar Sesión Actual"):
                st.session_state.current_session_id = None
                st.session_state.session_name = ""
                st.success("✅ Sesión cerrada")
                st.rerun()
    else:
        st.info("🔎 Selecciona o crea una sesión desde el sidebar para comenzar.")
        # Sugerencia rápida para crear sesión
        if st.button("➕ Crear sesión de prueba"):
            if poker.create_session("Sesión de Prueba", "Facilitador Demo"):
                st.success("✅ Sesión de prueba creada")
                st.rerun()

if __name__ == "__main__":
    main()
