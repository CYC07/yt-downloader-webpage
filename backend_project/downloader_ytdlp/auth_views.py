# downloader/auth_views.py
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

@api_view(['POST'])
@permission_classes([AllowAny]) # Anyone can register
def register_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email', '') # Optional email

    if not username or not password:
        return Response({'error': 'Username and password required'}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, password=password, email=email)
    return Response({'message': 'User created successfully'}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny]) # Anyone can try to log in
def login_user(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(request._request, username=username, password=password) # Use underlying HttpRequest for authenticate

    if user is not None:
        login(request._request, user) # Use underlying HttpRequest for login
        return Response({'message': 'Login successful', 'username': user.username})
    else:
        return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
# Default permission: IsAuthenticatedOrReadOnly, so only logged-in users can logout
def logout_user(request):
    logout(request._request) # Use underlying HttpRequest for logout
    return Response({'message': 'Logout successful'})

@api_view(['GET'])
def check_auth_status(request):
    if request.user.is_authenticated:
        return Response({'isAuthenticated': True, 'username': request.user.username})
    else:
        return Response({'isAuthenticated': False})