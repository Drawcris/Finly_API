from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from .models import Transaction, Category, Budget

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id','user', 'amount', 'type', 'category', 'date', 'description', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'icon']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ['id', 'category', 'amount', 'month']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class RegisterSerializer(serializers.Serializer):
   email = serializers.EmailField(
       required=True,
       validators=[UniqueValidator(queryset=User.objects.all())]
   )
   username = serializers.CharField(min_length=4, write_only=True, required=True, validators=[UniqueValidator(queryset=User.objects.all())])
   first_name = serializers.CharField(required=False, allow_blank=True)
   last_name = serializers.CharField(required=False, allow_blank=True)
   password = serializers.CharField(min_length=8, write_only=True, required=True)
   password2 = serializers.CharField(min_length=8, write_only=True, required=True)


   def validate(self, attrs):
       if attrs['password'] != attrs['password2']:
         raise serializers.ValidationError({"password": "Password fields didn't match."})
       validate_password(attrs['password'])
       return attrs

   def create(self, validated_data):
       user = User.objects.create_user(
           username=validated_data['username'],
           email=validated_data['email'],
           password=validated_data['password'],
           first_name=validated_data.get('first_name', ''),
           last_name=validated_data.get('last_name', ''),
       )
       return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']




