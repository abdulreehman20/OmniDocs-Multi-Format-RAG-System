
<!-- Neon Storage Integration Code -->
<!-- upload.py -->

```py
import os
import boto3

s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
bucket = "docs"
key = "uploads/file.txt"

s3.put_object(Bucket=bucket, Key=key, Body="Hello World!")

url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)
print(f"[view] {url}")
```

---------

<!-- PineCone Initiallization -->

```py
from pinecone import Pinecone

pc = Pinecone(api_key="********-****-****-****-************")
index = pc.Index("quickstart")
```

<!-- LangChain Models -->
nvidia/nemotron-3-ultra-550b-a55b:free -- use this model as our chat model
nvidia/nemotron-3.5-embed-1b:free -- use this as an embedding model