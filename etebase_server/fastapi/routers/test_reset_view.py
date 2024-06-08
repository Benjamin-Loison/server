from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from fastapi import APIRouter, Request, status

from etebase_server.django.utils import CallbackContext, get_user_queryset
from etebase_server.myauth.models import get_typed_user_model

from ..exceptions import HttpError
from ..msgpack import MsgpackRoute
from .authentication import SignupIn, signup_save

test_reset_view_router = APIRouter(route_class=MsgpackRoute, tags=["test helpers"])
User = get_typed_user_model()


@test_reset_view_router.post("/reset/", status_code=status.HTTP_204_NO_CONTENT)
def reset(data: SignupIn, request: Request):
    # Only run when in DEBUG mode! It's only used for tests
    if not settings.DEBUG:
        raise HttpError(code="generic", detail="Only allowed in debug mode.")

    with transaction.atomic():
        user_queryset = get_user_queryset(User.objects.all(), CallbackContext(request.path_params))
        user = get_object_or_404(user_queryset, username=data.user.username)
        # Only allow test users for extra safety
        if not getattr(user, User.USERNAME_FIELD).startswith("test_user"):
            raise HttpError(code="generic", detail="Endpoint not allowed for user.")

        if hasattr(user, "userinfo"):
            user.userinfo.delete()

        signup_save(data, request)
        # Delete all of the journal data for this user for a clear test env
        user.collection_set.all().delete()
        user.collectionmember_set.all().delete()
        user.incoming_invitations.all().delete()

        # FIXME: also delete chunk files!!!
