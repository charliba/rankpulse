"""Management command to generate a blog post via OpenAI."""
from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandParser

from apps.content.generator import ContentGenerator
from apps.content.models import ContentTopic, GeneratedPost
from apps.core.models import Site

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate a blog post using OpenAI. Provide a topic ID or title + keyword."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--topic-id", type=int, help="ContentTopic ID to generate for")
        parser.add_argument("--title", type=str, help="Post title (if no topic-id)")
        parser.add_argument("--keyword", type=str, help="Target keyword (if no topic-id)")
        parser.add_argument("--site-id", type=int, help="Site ID (if no topic-id)")
        parser.add_argument("--model", type=str, default="", help="OpenAI model override")

    def handle(self, *args, **options) -> None:
        topic_id = options.get("topic_id")
        title = options.get("title", "")
        keyword = options.get("keyword", "")
        site_id = options.get("site_id")
        model = options.get("model", "")

        topic = None
        site_name = ""
        site_domain = ""
        content_type = "blog_post"

        if topic_id:
            try:
                topic = ContentTopic.objects.select_related("cluster__site").get(pk=topic_id)
                title = topic.title
                keyword = topic.target_keyword
                content_type = topic.content_type
                site_name = topic.cluster.site.name
                site_domain = topic.cluster.site.domain
            except ContentTopic.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Topic #{topic_id} não encontrado."))
                return
        elif title and keyword:
            if site_id:
                try:
                    site = Site.objects.get(pk=site_id)
                    site_name = site.name
                    site_domain = site.domain
                except Site.DoesNotExist:
                    pass
        else:
            self.stdout.write(self.style.ERROR("Forneça --topic-id ou --title + --keyword"))
            return

        self.stdout.write(f"✍️  Gerando conteúdo...")
        self.stdout.write(f"   Título: {title}")
        self.stdout.write(f"   Keyword: {keyword}")
        self.stdout.write(f"   Tipo: {content_type}")

        generator = ContentGenerator(model=model)
        result = generator.generate_post(
            topic_title=title,
            target_keyword=keyword,
            site_name=site_name,
            site_domain=site_domain,
            content_type=content_type,
        )

        if result.get("error"):
            self.stdout.write(self.style.ERROR(f"Erro: {result['error']}"))
            return

        # Save if linked to topic
        if topic:
            post = GeneratedPost.objects.create(
                topic=topic,
                title=result["title"],
                slug=result["slug"],
                meta_description=result["meta_description"],
                content_html=result["content_html"],
                content_markdown=result.get("content_markdown", ""),
                word_count=result["word_count"],
                model_used=result["model_used"],
                prompt_used=result["prompt_used"],
                tokens_used=result["tokens_used"],
            )
            topic.status = "review"
            topic.save(update_fields=["status"])
            self.stdout.write(f"   Salvo: GeneratedPost #{post.pk}")

        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(f"Título: {result['title']}")
        self.stdout.write(f"Meta: {result['meta_description']}")
        self.stdout.write(f"Palavras: {result['word_count']}")
        self.stdout.write(f"Tokens: {result['tokens_used']}")
        self.stdout.write(f"Modelo: {result['model_used']}")
        self.stdout.write(self.style.SUCCESS("\n✅ Conteúdo gerado!"))
