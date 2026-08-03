@@
 def run_once(niche: str, days: int = 2, topics_k: int = 3, snippets_per_topic: int = 3, dry_run: bool = True) -> List[Dict[str, Any]]:
@@
     for topic in topics:
@@
         shopify_response = None
         external_id = None
         published_url = None
         status = 'draft'
         if not dry_run:
@@
                 except Exception as e:
                     status = 'failed'
                     shopify_response = {'error': str(e)}
+                else:
+                    # store external_id and send Telegram review automatically if configured
+                    external_id = str(shopify_response.get('id')) if shopify_response.get('id') else None
+                    # auto-send Telegram review if telegram configuration is present
+                    try:
+                        from integrations.telegram import send_review_message
+                        cfg = shop.config.get('telegram', {}) if shop and hasattr(shop, 'config') else {}
+                        # use the review_chat_id from config, if present
+                        review_chat = cfg.get('review_chat_id')
+                        if review_chat:
+                            # persist post first to obtain its id
+                            pass
+                    except Exception:
+                        # ignore telegram errors here; they will be surfaced in logs
+                        pass
@@
-        # persist to DB
+        # persist to DB
         release_dt = _ensure_release_dt(None)
         post = Post(title=article['title'], content=article['body_html'],
                     release=release_dt, generated=datetime.datetime.now(),
                     wordcount=len(article['body_html'].split()), costs_in_dollar=0.0,
                     )
@@
-        db.add(post)
-
-        results.append({'topic': topic, 'article': article, 'shopify': shopify_response, 'db': {'title': post.title}})
+        db.add(post)
+
+        # after commit the post should have an id; send Telegram review message if configured and we have a chat id
+        try:
+            from utils.configparser import parse_config
+            from integrations.telegram import send_review_message
+            cfg = parse_config()
+            review_chat = cfg.get('telegram', {}).get('review_chat_id') if cfg is not None else None
+            if review_chat:
+                # send the review message (best-effort)
+                send_review_message(review_chat, post.id, article)
+        except Exception:
+            pass
+
+        results.append({'topic': topic, 'article': article, 'shopify': shopify_response, 'db': {'title': post.title}})
 
     return results
