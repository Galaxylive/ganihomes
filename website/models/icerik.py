# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse
from django.db import models
from datetime import datetime
from django.utils.translation import ugettext_lazy as _
from managers import EtkinManager
from mptt.models import MPTTModel, TreeForeignKey
from dil import Dil
from medya import Medya
from tinymce import models as tinymce_models
from south.modelsinspector import add_introspection_rules
from utils.cache import kes
from website.models.dil import Ceviriler
from django.conf import settings

add_introspection_rules([], ["^tinymce.models.HTMLField"])

from glob import iglob

def sablonListesi():
    dizin = settings.TEMPLATE_DIRS[0]
    #    assert 0, dizin
    return [('', u'Varsayılan')] + [[t.replace(dizin, '')] * 2 for t in iglob(dizin + '/kullanici_sablonlari/*.html')]


class Sayfa(MPTTModel):
    """
    belgelendirme eksik !!!!!!!!
    """
    KES_PREFIX = 'SayfaBaslik'
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', verbose_name='Üst Sayfa')
    pul = models.DateTimeField(u"Kayıt Zamanı", auto_now_add=True)
    sablon = models.CharField(max_length=200, null=True, blank=True, choices=sablonListesi(),
                              help_text=u'Bu içeriği standart dışı bir şablonla göstermek istiyorsanız buradan seçebilirsiniz. <br><b style="color:red">!!! Lütfen emin değilseniz bu ayarı kesinlikle değiştirmeyiniz !!!</b>')
    # navigasyon
    menude = models.BooleanField(u"Menüde", default=True)
    etkin = models.BooleanField(u"Yayında", default=True, help_text=u"Sayfa yayında mı?")
    sadece_uyeler = models.BooleanField(u"Sadece üyeler görebilir", help_text=u"Bu sayfayı sadece üyeler görebilir.")
    medya = models.ManyToManyField(Medya, null=True, blank=True)
    #    objects = models.Manager()
    #    etkinler = EtkinManager()

    def __unicode__(self):
        return  '%s' % (self.baslik(),)

    def baslik(self):
        k = kes('sayfabaslik', self.id)
        try:
            return k.g() or k.s(self.icerik_set.all()[0].baslik[:20])
        except:
            return self.id

    baslik.short_description = u'Başlık'
    #    baslik.admin_order_field  = ''
    baslik.allow_tags = True

    def al_baslik(self, dilkodu):
        k = kes('dsayfabaslik', dilkodu, self.id)
        return k.g() or k.s(self.al_icerik(dilkodu).al_menu_baslik())


    def al_url(self, dilkodu):
        k = kes('sayfaurl', dilkodu, self.id)
        return k.g() or k.s(self.al_icerik(dilkodu).get_absolute_url(dilkodu))


    def al_icerik(self, dilkodu):
        try:
            return self.icerik_set.get(dil_kodu=dilkodu)
        except:
            return self.icerik_set.all()[0]

    @classmethod
    def al_anasayfa(cls):
        a = cls.objects.filter(parent__isnull=True)
        return a[0] if a else None

    def kategoriler(self, dilkodu):
        ks = kes('kategoriler', dilkodu, self.id)
        menu = ks.g([])
        if not menu:
            kat = self if self.get_descendant_count() else self.parent
            for k in kat.get_siblings(include_self=True):
                ogeler = []
                for s in k.get_children():
                    ogeler.append({'baslik': s.al_baslik(dilkodu), 'url': s.al_url(dilkodu), 'etkin': s.id == self.id})
                menu.append({'baslik': k.al_baslik(dilkodu), 'url': k.al_url(dilkodu), 'etkin': k.id == self.id,
                             'ogeler': ogeler})
            ks.s(menu)
        return menu

    @classmethod
    def al_menu(cls, dilkodu):
        ks = kes('anamenu', dilkodu)
        menu = ks.g([])
        if not menu:
            ana = cls.al_anasayfa()
            if ana:
                for k in ana.get_children().filter(menude=True):
                    menu.append({'id': k.id, 'baslik': k.al_baslik(dilkodu), 'url': k.al_url(dilkodu), })
                ks.s(menu)
        return menu

    class Meta:
        verbose_name = u"Web Sayfası"
        verbose_name_plural = u"Web Sayfaları"
        app_label = 'website'
    #        ordering = ['site__id','ust__id','sira']
    #get_latest_by=''
    #order_with_respect_to = ''
    #unique_together = (("", ""),)
    #permissions = (("can_do_something", "Can do something"),)


class Icerik(models.Model):
    dil = models.ForeignKey(Dil, verbose_name=_('Dil'))
    dil_kodu = models.CharField(max_length=5, editable=False, db_index=True)
    #    sablon = models.CharField(max_length=200, null=True, blank=True,choices=[('',u'Seçiniz'),],help_text=u'Bu içeriği standart dışı bir şablonla göstermek istiyorsanız buradan seçebilirsiniz. <br><b>!!! Lütfen emin değilseniz bu ayarı değiştirmeyiniz !!!</b>', editable=False)
    metin = tinymce_models.HTMLField(_("İçerik Gövdesi"), blank=True, null=True)
    baslik = models.CharField(_("başlık"), max_length=255)
    menu_baslik = models.CharField(_("menü başlık"), max_length=255, blank=True, null=True,
                                   help_text=_("Menüde başlığın üzerine yazmak için"))
    slug = models.SlugField(_("slug"), max_length=255, db_index=True, unique=False,
                            help_text='Sayfa adresi. (otomatik üretilir)')
    url = models.CharField(_("URL'ye Yönlen"), max_length=255, db_index=True, null=True, blank=True)
    #    redirect = models.CharField(_("yönlen"), max_length=255, blank=True, null=True)
    tanim = models.TextField(_("meta tanım"), max_length=255, blank=True, null=True)
    anahtar = models.CharField(_("meta anahtar kelimeler"), max_length=255, blank=True, null=True)
    html_baslik = models.CharField(_("html başlığı"), max_length=255, blank=True, null=True,
                                   help_text=_("tarayıcı  başlığının üzerine yaz"))
    sayfa = models.ForeignKey(Sayfa, verbose_name=_("Sayfa"))
    olusturma = models.DateTimeField(_("oluşturulma zamanı"), editable=False, default=datetime.now)
    guncelleme = models.DateTimeField(null=True, blank=True, auto_now=True)

    def get_absolute_url(self, force_lang=None):
        if not self.url:
            return  '/%s/%s/%s/' % (force_lang or self.dil_kodu, self.sayfa.id, self.slug)
        else:
            return '%s?sayfa_id=%s' % (self.url, self.sayfa.id) if 'http' not in self.url else self.url

    def al_menu_baslik(self):
        return self.menu_baslik or self.baslik

    class Meta:
        unique_together = (('dil', 'sayfa'),)
        verbose_name = u"Web Sayfası İçeriği"
        verbose_name_plural = u"Web Sayfası İçerikleri"
        app_label = 'website'

    def __unicode__(self):
        return "%s (%s)" % (self.baslik, self.slug)


    def save(self, *args, **kwargs):
        self.dil_kodu = self.dil.kodu
        super(Icerik, self).save(*args, **kwargs)

#    @property
#    def overwrite_url(self):
#        """Return overrwriten url, or None
#        """
#        if self.has_url_overwrite:
#            return self.path
#        return None
# Create your models here.



class Haber(models.Model):
    """
    belgelendirme eksik !!!!!!!!
    """
    dil = models.ForeignKey(Dil, verbose_name=_('Dil'))
    dil_kodu = models.CharField(max_length=5, editable=False, db_index=True)
    baslik = models.CharField(u"Başlık", max_length=200, help_text=u"Sayfa Başlığı")
    slug = models.SlugField(u"URL Başlık",
                            help_text=u"Sayfa başlığının adres satırında görenecek hali. Türkçe karakterler haricindeki harfleri, rakamları ve tire işaretini kullanabilirsiniz.")
    anahtar_kelime = models.CharField(u"Anahtar Kelimeler", max_length=250,
                                      help_text=u"Sayfa içeriyle ilgili anahtar kelimeleri virgülle ayrılmış olarak girebilirsiniz."
                                      , null=True, blank=True)
    tanim = models.CharField(u'Anasayfa Özeti', max_length=100,
                             help_text=u"Haberin 100 karakteri geçmeyecek, anasayfada görnecek kısa bir özetini giriniz."
                             , null=True, blank=True)
    icerik = tinymce_models.HTMLField(u'Haber İçeriği')
    pul = models.DateTimeField(u"Kayıt Zamanı", auto_now_add=True)
    son_guncelleme = models.DateTimeField(null=True, blank=True, auto_now=True)
    etkin = models.BooleanField(u"Yayında", default=True, help_text=u"Sayfa yayında mı?")
    sabit = models.BooleanField(u"Tepeye sabitle", default=False,
                                help_text=u"Kronolojik sıralamayı yok sayıp bu haberi en başta göster?")
    medya = models.ManyToManyField(Medya, null=True, blank=True)


    def get_absolute_url(self, force_lang=None):
        return '/%s%s' % (force_lang or self.dil_kodu, reverse('haber_goster', args=[self.slug, self.id]))

    @classmethod
    def al_son_haber(cls, dilkodu):
        h = cls.objects.filter(etkin=True, dil_kodu=dilkodu)
        return h[0] if h else None

    #= models.CharField(u"",max_length=)
    #= models.SmallIntegerField(u"")
    #= models.IntegerField(u"")
    #= models.DecimalField(u"", max_digits=4, default=Decimal('0.0'),  decimal_places=2, )
    #= models.TextField(u"",help_text="",null=True,blank=True)
    #= models.DateField(u"", null=True, blank=True)
    #= models.DateTimeField(u"",  null=True,  blank=True )

    def kategoriler(self, dilkodu):
        ks = kes('haberler', dilkodu, self.id)
        haberler = ks.g([])
        if not haberler:
            for s in Haber.objects.filter(etkin=True, dil_kodu=dilkodu)[:10]:
                haberler.append({'baslik': s.baslik, 'url': s.get_absolute_url(dilkodu), 'etkin': s.id == self.id})
            ks.s(haberler)
        return [{'ogeler': haberler, 'baslik': Ceviriler.cevir('News', dilkodu), 'url': '#'}]

    def __unicode__(self):
        return  '%s' % (self.baslik,)


    class Meta:
        verbose_name = u"Haber Kaydı"
        verbose_name_plural = u"Haber Kayıtları"
        ordering = ['-sabit', '-pul']
        app_label = 'website'
        #get_latest_by=''
        #order_with_respect_to = ''
        #unique_together = (("", ""),)
        #permissions = (("can_do_something", "Can do something"),)

    def save(self, *args, **kwargs):
        self.dil_kodu = self.dil.kodu
        super(Haber, self).save(*args, **kwargs)


SIRA = [(s, s) for s in range(20)]
class Vitrin(models.Model):
    """
    belgelendirme eksik !!!!!!!!
    """
    BANNERLER = ( (1, 'Anasayfa'), (2, 'Altsayfa') )
    banner = models.SmallIntegerField(_('Banner Tipi'), help_text='Bu görsel hangi bannerda gösterilecek.',
                                      choices=BANNERLER)
    dil = models.ForeignKey(Dil, verbose_name=_('Dil'), null=True, blank=True,
                            help_text='Boş bırakabilirsiniz. Hiç dil seçimi yapmazsanız tüm dillerde aynı slidelar gösterilir.')
    dil_kodu = models.CharField(max_length=5, editable=False, db_index=True, null=True, blank=True)
    #    ad = models.CharField(u"Slayt Başlığı", max_length=100, help_text=u"Fare ile slaytın üzerine gelince görülecek açıklama.",null=True,blank=True, editable=False)
    gorsel = models.ImageField(u"Vitrin Görseli", upload_to='vitrin', null=True, blank=True)
    #    url = models.CharField(u"URL", max_length=100, help_text=u"Slayta tıklanınca gidilecek url.",null=True,blank=True)
    #    icerik = models.TextField(u'İçerik',help_text=u"Buraya gireceğiniz içerik slaytın üzerinde gösterilir.", null=True, blank=True, editable=False)
    pul = models.DateTimeField(u"Kayıt Zamanı", auto_now_add=True)
    etkin = models.BooleanField(u"Yayında", default=True)
    sira = models.SmallIntegerField(u"Sıralama", choices=SIRA, db_index=True)
    objects = models.Manager()
    etkinler = EtkinManager()

    @classmethod
    def al_slide(cls, banner_tip, dilkodu=None):
        ogeler = cls.etkinler.filter(banner=banner_tip)
        if dilkodu:
            dilli_ogeler = ogeler.filter(dil_kodu=dilkodu)
            return dilli_ogeler if len(dilli_ogeler) else ogeler

#        o = o if dilkodu is None else o.filter(dil_kodu=dilkodu)

    #= models.CharField(u"",max_length=)
    #= models.SmallIntegerField(u"")
    #= models.IntegerField(u"")
    #= models.DecimalField(u"", max_digits=4, default=Decimal('0.0'),  decimal_places=2, )
    #= models.TextField(u"",help_text="",null=True,blank=True)
    #= models.DateField(u"", null=True, blank=True)
    #= models.DateTimeField(u"",  null=True,  blank=True )


    def __unicode__(self):
        return  '%s (%s)' % (self.sira, self.gorsel.name)


    class Meta:
        verbose_name = u"Vitrin Ögesi"
        verbose_name_plural = u"Vitrin Ögeleri"
        ordering = ['sira', ]
        app_label = 'website'
        #get_latest_by=''
        #order_with_respect_to = ''
        #unique_together = (("", ""),)
        #permissions = (("can_do_something", "Can do something"),)

    def save(self, *args, **kwargs):
        if self.dil:
            self.dil_kodu = self.dil.kodu
        super(Vitrin, self).save(*args, **kwargs)