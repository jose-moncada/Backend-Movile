from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import TareasSerializer
from .authentication import FirebaseAuthentication
from backend.firebase_config import get_firestore_client
from firebase_admin import firestore

db = get_firestore_client()

class TareaAPIView(APIView):

    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]

    # =========================
    # GET - Traer tareas del usuario
    # =========================
    def get(self, request, tarea_id=None):

        uid_usuario = request.user.uid
        rol_usuario = request.user.rol

        # Parametros de la consulta
        limit = int(request.query_params.get('limit', 10)) # 10 es el limite por defecto
        last_doc_id = request.query_params.get('last_doc_id')

        # Definir la consulta dependiendo el rol
        if rol_usuario == 'instructor':
            query = db.collection('api_tareas')
            mensaje = "Listando como rol de instructor"
        else:
            # Se filtra por su uid
            query = db.collection('api_tareas').where('usuario_id', '==', uid_usuario)
            mensaje = "Listado como aprendiz"

        #Ordenar
        query = query.order_by('fecha_creacion')

        # Logica de la paginación
        if last_doc_id:
            last_doc = db.collection('api_tareas').document(last_doc_id).get()
            if last_doc.exists:
                query = query.start_after(last_doc)

        # Aplica el limite
        docs = query.limit(limit).stream()
        
        tareas = []
        for doc in docs:
            tarea_data = doc.to_dict()
            tarea_data['id'] = doc.id
            tareas.append(tarea_data)

        return Response({"mensaje": mensaje,
                        "Total en pagina" : len(tareas),
                        "datos": tareas,
                        "next_page_token": tareas[-1]['id'] if tareas else None
                        }, status=status.HTTP_200_OK)

    # =========================
    # POST - Crear tarea
    # =========================
    def post(self, request):

        serializer = TareasSerializer(data=request.data)

        if serializer.is_valid():

            datos_validados = serializer.validated_data
            datos_validados['usuario_id'] = request.user.uid
            datos_validados['fecha_creacion'] = firestore.SERVER_TIMESTAMP

            try:
                nuevo_doc = db.collection('api_tareas').add(datos_validados)
                id_generado = nuevo_doc[1].id

                return Response(
                    {
                        "mensaje": "Tarea creada correctamente",
                        "id": id_generado
                    },
                    status=status.HTTP_201_CREATED
                )

            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # =========================
    # PUT - Actualizar tarea
    # =========================
    def put(self, request, tarea_id=None):

        if not tarea_id:
            return Response(
                {"error": "El ID es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            tarea_ref = db.collection('api_tareas').document(tarea_id)
            doc = tarea_ref.get()

            if not doc.exists:
                return Response(
                    {"error": "No encontrado"},
                    status=status.HTTP_404_NOT_FOUND
                )

            tarea_data = doc.to_dict()

            if tarea_data.get('usuario_id') != request.user.uid:
                return Response(
                    {"error": "No tienes acceso a esta tarea"},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = TareasSerializer(
                data=request.data,
                partial=True
            )

            if serializer.is_valid():
                tarea_ref.update(serializer.validated_data)

                return Response(
                    {
                        "mensaje": f"Tarea {tarea_id} actualizada",
                        "datos": serializer.validated_data
                    },
                    status=status.HTTP_200_OK
                )

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # =========================
    # DELETE - Eliminar tarea
    # =========================
    def delete(self, request, tarea_id=None):

        if not tarea_id:
            return Response(
                {"error": "El ID es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            tarea_ref = db.collection('api_tareas').document(tarea_id)
            doc = tarea_ref.get()

            if not doc.exists:
                return Response(
                    {"error": "No encontrado"},
                    status=status.HTTP_404_NOT_FOUND
                )

            tarea_data = doc.to_dict()

            if tarea_data.get("usuario_id") != request.user.uid:
                return Response(
                    {"error": "No tienes permiso para eliminar esta tarea"},
                    status=status.HTTP_403_FORBIDDEN
                )

            tarea_ref.delete()

            return Response(
                {"mensaje": f"Tarea {tarea_id} eliminada"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )