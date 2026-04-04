from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status
from tresenraya.serializers import RegistroSerializer

class RegistroView(APIView):
    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        if serializer.is_valid():
            # Guardamos el usuario
            user = serializer.save()
            
            # Generamos el token para el nuevo usuario
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                "token": token.key,
                "username": user.username,
                "message": "Usuario creado con éxito."
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
