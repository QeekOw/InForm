# Modal deployment

The demo API runs at https://cliffow29--inform-api.modal.run.
It uses the public `QeeeeK/donut-inbody` checkpoint at the revision pinned in
`modal_deploy.py`. The model is included in the image, so cold starts do not
download it again.

```sh
uv tool install modal
modal token new
modal deploy modal_deploy.py
python tests/smoke_modal.py https://cliffow29--inform-api.modal.run
```

On this Windows machine, the network certificate requires the system trust store.
The deployment command used was:

```powershell
$env:PYTHONUTF8 = "1"
uv --system-certs run --no-project --python 3.12 --with modal --with truststore python -c "import truststore,runpy; truststore.inject_into_ssl(); runpy.run_module('modal',run_name='__main__')" deploy modal_deploy.py
```

Set Vercel's production `NEXT_PUBLIC_API_URL` to that API URL and redeploy the
frontend for the new value to take effect.

CPU is the default and was deployed without adding a payment method. Usage
consumes Modal's monthly free credits; this is not unlimited free hosting.
One container handles requests and shuts down after five minutes of inactivity.
Read jobs are held in memory and disappear when the container stops or redeploys;
users should finish confirmation and generate their plan during the same session.
Live reads are serialized to keep memory use bounded while polling remains concurrent.
