# HyperPod Launcher Example

Run from the `launcher/` directory:

```bash
./hyperpod_launcher.sh \
    --recipe ../micro_pt_recipe.yaml \
    --namespace kubeflow \
    --name dewanup-cpt-nodm-ce-chkpt \
    --instance-type ml.p5.48xlarge \
    --container 708977205387.dkr.ecr.us-east-1.amazonaws.com/nova-fine-tune-repo:SM-HP-CPT-V2-BETA-latest \
    --data s3://618100645563-nova-customization-beta/dewanup/data/cpt/train.jsonl \
    --val s3://618100645563-nova-customization-beta/dewanup/data/cpt/validation.jsonl \
    --output s3://618100645563-nova-customization-beta/dewanup/output/ \
    --mlflow arn:aws:sagemaker:us-east-1:618100645563:mlflow-app/app-QYBQZINLZDLY
```

Or use the Python version:

```bash
python3 hyperpod_launcher.py \
    --recipe ../micro_pt_recipe.yaml \
    --namespace kubeflow \
    --name dewanup-cpt-nodm-ce-chkpt \
    --instance-type ml.p5.48xlarge \
    --container 708977205387.dkr.ecr.us-east-1.amazonaws.com/nova-fine-tune-repo:SM-HP-CPT-V2-BETA-latest \
    --data s3://618100645563-nova-customization-beta/dewanup/data/cpt/train.jsonl \
    --val s3://618100645563-nova-customization-beta/dewanup/data/cpt/validation.jsonl \
    --output s3://618100645563-nova-customization-beta/dewanup/output/ \
    --mlflow arn:aws:sagemaker:us-east-1:618100645563:mlflow-app/app-QYBQZINLZDLY
```
