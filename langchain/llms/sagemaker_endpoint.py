"""Wrapper around Sagemaker InvokeEndpoint API."""
import json
from typing import Any, Callable, Dict, List, Mapping, Optional

from pydantic import BaseModel, Extra, root_validator

from langchain.llms.base import LLM
from langchain.llms.utils import enforce_stop_tokens


VALID_TASKS = ("text2text-generation", "text-generation")

class SagemakerEndpoint(LLM, BaseModel):
    """Wrapper around custom Sagemaker Inference Endpoints.

    To use, you must supply the endpoint name from your deployed
    Sagemaker model & the region where it is deployed.

    To authenticate, the AWS client uses the following methods to
    automatically load credentials:
    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html

    If a specific credential profile should be used, you must pass
    the name of the profile from the ~/.aws/credentials file that is to be used.

    Make sure the credentials / roles used have the required policies to
    access the Sagemaker endpoint.
    See: https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html
    """

    """
    Example:
        .. code-block:: python

            from langchain import SagemakerEndpoint
            import sagemaker
            endpoint_name = "some-endpoint"
            sagemaker_runtime_client=boto_session.client(
                        'sagemaker-runtime',
                        region_name='<region>'
                    )

            # Obtain SageMaker session from boto3 session and sagemaker runtime
            sagemaker_session=sagemaker.Session(
                boto_session,
                sagemaker_runtime_client=sagemaker_runtime_client,
            )
            se = SagemakerEndpoint(
                endpoint_name=endpoint_name,
                region_name=region_name,
                sagemaker_session=sagemaker_session,
                task="text-generation"
            )
    """
    client: Any  #: :meta private:
    endpoint_name: str
    """sagemaker endpoint to use."""
    sagemaker_session: Any
    """Manage interactions with the Amazon SageMaker APIs and any other AWS services needed.."""
    task: str
    """Task to call the model with. Should be a task that returns `generated_text`."""
    model_kwargs: Optional[dict] = None

    model_kwargs: Optional[Dict] = None
    """Key word arguments to pass to the model."""

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        """Validate that api key and python package exists in environment."""
        try:
            from sagemaker.predictor import Predictor
            from sagemaker.serializers import JSONSerializer
            from sagemaker.deserializers import JSONDeserializer
  
            endpoint_name = values["endpoint_name"]
            sagemaker_session = values["sagemaker_session"]
            predictor = Predictor(
                            endpoint_name,
                            sagemaker_session=sagemaker_session, 
                            serializer=JSONSerializer(), 
                            deserializer=JSONDeserializer()
                            )      
            values["client"] = predictor
            task = values.get("task")
            if task not in VALID_TASKS:
                    raise ValueError(
                        f"Got invalid task {task}, "
                        f"currently only {VALID_TASKS} are supported"
                    )
        except ImportError:
            raise ValueError(
                "Could not import sagemaker python package. "
                "Please install sagemaker `pip install sagemaker`."
            )
        return values

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        _model_kwargs = self.model_kwargs or {}
        return {
            **{"endpoint_name": self.endpoint_name},
            **{"model_kwargs": _model_kwargs},
        }

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "sagemaker_endpoint"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """Call out to Sagemaker inference endpoint.

        Args:
            prompt: The prompt to pass into the model.
            stop: Optional list of stop words to use when generating.

        Returns:
            The string generated by the model.

        Example:
            .. code-block:: python

                response = se("Tell me a joke.")
        """
        # send request
        try:
            response = self.client.predict({"inputs": prompt})
        except Exception as e:
            raise ValueError(f"Error raised by inference endpoint: {e}")
        if "error" in response:
            raise ValueError(f"Error raised by inference API: {response['error']}")
        return response[0]["generated_text"]